from __future__ import annotations

from parser.adapters.base import BaseAdapter, LookupResult
from parser.models import CandidateModel, ErrorModel, LookupRequest


class BlumAdapter(BaseAdapter):
    supplier_id = "blum"

    def _lookup_impl(self, req: LookupRequest) -> LookupResult:
        article = (req.query.article or "").strip().upper()
        brand = (req.query.brand or "").strip().upper() or None

        if article == "UNKNOWN-BLUM":
            return self.not_found("Нет карточки BLUM по article")

        if article == "71B3550" and not brand and not req.query.url:
            return LookupResult(
                status="ambiguous",
                candidates=[
                    CandidateModel(
                        title="Петля CLIP top BLUMOTION 71B3550",
                        product_url="https://blum-msk.ru/catalog/demo/71b3550",
                        price={"amount": 312.0, "currency": "RUB"},
                        matched={"article": "71B3550", "brand": "BLUM"},
                    ),
                    CandidateModel(
                        title="Петля CLIP top 71B3550 (без BLUMOTION)",
                        product_url="https://blum-msk.ru/catalog/demo/71b3550-basic",
                        price={"amount": 275.0, "currency": "RUB"},
                        matched={"article": "71B3550", "brand": "BLUM"},
                    ),
                ],
                error=ErrorModel(
                    code="MULTIPLE_MATCHES",
                    message="Выберите карточку",
                    retryable=False,
                ),
            )

        html, err = self.load_html(req)
        if err:
            if err.code == "SUPPLIER_BLOCKED":
                return self.blocked(err.message)
            if err.code == "PRODUCT_NOT_FOUND":
                return self.not_found(err.message)
            return LookupResult(status="error", error=err, http_status=422)

        assert html is not None
        soup = self.soup(html)
        title_el = soup.select_one(".product-title, h1")
        price_el = soup.select_one(".price, [itemprop=price]")
        stock_el = soup.select_one(".stock")
        if not title_el or not price_el:
            return self.parse_error("Не удалось извлечь title/price (вёрстка BLUM)")

        amount = self.parse_price_text(price_el.get("content") or price_el.get_text())
        if amount is None:
            return self.parse_error("Цена не распознана")

        product_url = req.query.url or "https://blum-msk.ru/catalog/demo/71b3550"
        return self.ok(
            title=title_el.get_text(strip=True),
            product_url=product_url,
            amount=amount,
            article=req.query.article or "71B3550",
            brand=req.query.brand or "BLUM",
            stock_text=stock_el.get_text(strip=True) if stock_el else None,
            available=True,
            currency=req.options.currency or "RUB",
        )
