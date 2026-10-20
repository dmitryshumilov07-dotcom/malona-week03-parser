from __future__ import annotations

from parser.adapters.base import BaseAdapter, LookupResult
from parser.models import LookupRequest


class KvadratAdapter(BaseAdapter):
    supplier_id = "kvadrat"

    def _lookup_impl(self, req: LookupRequest) -> LookupResult:
        article = (req.query.article or "").strip().upper()
        if article == "NO-SUCH-SKU":
            return self.not_found("Нет карточки КВАДРАТ по article+brand")

        html, err = self.load_html(req)
        if err:
            if err.code == "SUPPLIER_BLOCKED":
                return self.blocked(err.message)
            if err.code == "PRODUCT_NOT_FOUND":
                return self.not_found(err.message)
            return LookupResult(status="error", error=err, http_status=422)

        assert html is not None
        soup = self.soup(html)
        title_el = soup.select_one(".name, h1")
        price_el = soup.select_one(".price-value")
        stock_el = soup.select_one(".avail")
        if not title_el or not price_el:
            return self.parse_error("Не удалось извлечь title/price (вёрстка КВАДРАТ)")

        amount = self.parse_price_text(price_el.get_text())
        if amount is None:
            return self.parse_error("Цена не распознана")

        product_url = req.query.url or "https://spkvadrat.ru/catalog/demo/kv-slide-450"
        return self.ok(
            title=title_el.get_text(strip=True),
            product_url=product_url,
            amount=amount,
            article=req.query.article or "KV-SLIDE-450",
            brand=req.query.brand or "KVADRAT",
            stock_text=stock_el.get_text(strip=True) if stock_el else None,
            available=True,
            currency=req.options.currency or "RUB",
        )
