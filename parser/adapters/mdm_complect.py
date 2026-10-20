from __future__ import annotations

from parser.adapters.base import BaseAdapter, LookupResult
from parser.models import LookupRequest


class MdmComplectAdapter(BaseAdapter):
    supplier_id = "mdm-complect"

    def _lookup_impl(self, req: LookupRequest) -> LookupResult:
        article = (req.query.article or "").strip().upper()
        if article == "UNKNOWN":
            return self.not_found("Нет карточки MDM по article")

        html, err = self.load_html(req)
        if err:
            if err.code == "SUPPLIER_BLOCKED":
                return self.blocked(err.message)
            if err.code == "PRODUCT_NOT_FOUND":
                return self.not_found(err.message)
            return LookupResult(status="error", error=err, http_status=422)

        assert html is not None
        soup = self.soup(html)
        title_el = soup.select_one("#product h1, h1")
        price_el = soup.select_one(".product-price")
        stock_el = soup.select_one(".availability")
        if not title_el or not price_el:
            return self.parse_error("Не удалось извлечь title/price (вёрстка MDM)")

        raw = price_el.get("data-price") or price_el.get_text()
        amount = self.parse_price_text(str(raw))
        if amount is None:
            return self.parse_error("Цена не распознана")

        product_url = req.query.url or "https://www.mdm-complect.ru/catalog/demo-product-001"
        available = None
        stock_text = stock_el.get_text(strip=True) if stock_el else None
        if stock_text:
            available = "налич" in stock_text.lower()

        return self.ok(
            title=title_el.get_text(strip=True),
            product_url=product_url,
            amount=amount,
            article=req.query.article or "MDM-DEMO-001",
            brand=req.query.brand or "MDM",
            stock_text=stock_text,
            available=available,
            confidence=0.9,
            currency=req.options.currency or "RUB",
        )
