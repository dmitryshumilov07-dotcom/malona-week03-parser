from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

from parser.models import (
    CandidateModel,
    ErrorModel,
    LookupRequest,
    LookupResponse,
    MatchedModel,
    MetaModel,
    PriceModel,
    StockModel,
)
from parser.settings import get_settings
from parser.whitelist import find_snapshot, is_allowed


CAPTCHA_MARKERS = (
    "captcha",
    "are you not a robot",
    "не робот",
    "cloudflare",
    "access denied",
    "attention required",
)


@dataclass
class LookupResult:
    status: str
    matched: MatchedModel | None = None
    price: PriceModel | None = None
    stock: StockModel | None = None
    candidates: list[CandidateModel] = field(default_factory=list)
    error: ErrorModel | None = None
    confidence: float = 0.95
    http_status: int | None = None


class BaseAdapter(ABC):
    supplier_id: str

    def __init__(self) -> None:
        self.settings = get_settings()

    def lookup(self, req: LookupRequest) -> LookupResponse:
        article = req.query.article
        url = req.query.url

        if not is_allowed(self.supplier_id, article, url):
            return self._resp(
                req,
                self.not_found("Запрос вне whitelist fixtures/suppliers_test_queries.yaml"),
            )

        result = self._lookup_impl(req)
        return self._resp(req, result)

    @abstractmethod
    def _lookup_impl(self, req: LookupRequest) -> LookupResult:
        raise NotImplementedError

    def _resp(
        self,
        req: LookupRequest,
        result: LookupResult,
        force_status: str | None = None,
    ) -> LookupResponse:
        status = force_status or result.status
        meta = None
        if status == "ok":
            meta = MetaModel(
                fetched_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                parser_version=self.settings.parser_version,
                confidence=result.confidence,
                cache_hit=False,
            )
        return LookupResponse(
            request_id=req.request_id,
            status=status,  # type: ignore[arg-type]
            supplier_id=self.supplier_id,
            matched=result.matched,
            price=result.price,
            stock=result.stock if req.options.need_stock or result.stock else result.stock,
            meta=meta,
            candidates=result.candidates or None,
            error=result.error,
        )

    def load_html(self, req: LookupRequest) -> tuple[str | None, ErrorModel | None]:
        """Prefer snapshots when enabled; otherwise try live URL from whitelist."""
        snap = find_snapshot(self.supplier_id, req.query.article, req.query.url)
        if self.settings.parser_use_page_snapshots and snap and Path(snap).is_file():
            return Path(snap).read_text(encoding="utf-8"), None

        url = req.query.url
        if not url:
            return None, ErrorModel(
                code="PRODUCT_NOT_FOUND",
                message="Нет URL для live-запроса и snapshot недоступен",
                retryable=False,
            )

        try:
            timeout = max(1.0, req.options.timeout_ms / 1000.0)
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                r = client.get(
                    url,
                    headers={"User-Agent": "MalinaParser/1.0 (+internship; whitelist-only)"},
                )
            text = r.text
            if r.status_code in (403, 429) or self.looks_like_captcha(text):
                return None, ErrorModel(
                    code="SUPPLIER_BLOCKED",
                    message=f"Сайт вернул anti-bot/captcha (HTTP {r.status_code})",
                    retryable=True,
                )
            if r.status_code >= 400:
                return None, ErrorModel(
                    code="PARSE_ERROR",
                    message=f"HTTP {r.status_code} от поставщика",
                    retryable=False,
                )
            return text, None
        except httpx.TimeoutException:
            return None, ErrorModel(
                code="SUPPLIER_TIMEOUT",
                message="Таймаут при обращении к сайту поставщика",
                retryable=True,
            )
        except httpx.HTTPError as exc:
            return None, ErrorModel(
                code="PARSE_ERROR",
                message=f"Ошибка HTTP-клиента: {exc.__class__.__name__}",
                retryable=True,
            )

    @staticmethod
    def looks_like_captcha(html: str) -> bool:
        low = html.lower()
        return any(m in low for m in CAPTCHA_MARKERS)

    @staticmethod
    def parse_price_text(text: str) -> float | None:
        cleaned = text.replace("\xa0", " ").replace(" ", "")
        m = re.search(r"(\d+)(?:[.,](\d{1,2}))?", cleaned)
        if not m:
            return None
        whole = m.group(1)
        frac = m.group(2) or "0"
        return round(float(f"{whole}.{frac}"), 2)

    @staticmethod
    def soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    def not_found(self, message: str = "Карточка не найдена") -> LookupResult:
        return LookupResult(
            status="not_found",
            error=ErrorModel(code="PRODUCT_NOT_FOUND", message=message, retryable=False),
        )

    def blocked(self, message: str) -> LookupResult:
        return LookupResult(
            status="error",
            error=ErrorModel(code="SUPPLIER_BLOCKED", message=message, retryable=True),
            http_status=422,
        )

    def parse_error(self, message: str) -> LookupResult:
        return LookupResult(
            status="error",
            error=ErrorModel(code="PARSE_ERROR", message=message, retryable=False),
            http_status=422,
        )

    def ok(
        self,
        *,
        title: str,
        product_url: str,
        amount: float,
        article: str | None,
        brand: str | None,
        stock_text: str | None = None,
        available: bool | None = True,
        confidence: float = 0.95,
        currency: str = "RUB",
    ) -> LookupResult:
        return LookupResult(
            status="ok",
            matched=MatchedModel(
                article=article,
                brand=brand,
                title=title,
                product_url=product_url,
            ),
            price=PriceModel(amount=amount, currency=currency, vat_included=True, price_type="retail"),
            stock=StockModel(available=available, quantity_text=stock_text),
            confidence=confidence,
        )
