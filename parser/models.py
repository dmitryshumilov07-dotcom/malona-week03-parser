from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class QueryModel(BaseModel):
    article: str | None = None
    brand: str | None = None
    name: str | None = None
    oem: str | None = None
    url: str | None = None

    @model_validator(mode="after")
    def require_article_or_url(self) -> "QueryModel":
        if not (self.article or self.url):
            raise ValueError("query.url or query.article is required")
        return self


class OptionsModel(BaseModel):
    need_stock: bool = False
    currency: str = "RUB"
    timeout_ms: int = 25000


class LookupRequest(BaseModel):
    request_id: str
    supplier_id: str
    query: QueryModel
    options: OptionsModel = Field(default_factory=OptionsModel)


class PriceModel(BaseModel):
    amount: float
    currency: str = "RUB"
    vat_included: bool = True
    price_type: Literal["retail", "wholesale", "unknown"] = "retail"


class MatchedModel(BaseModel):
    article: str | None = None
    brand: str | None = None
    title: str | None = None
    product_url: str


class StockModel(BaseModel):
    available: bool | None = None
    quantity_text: str | None = None


class MetaModel(BaseModel):
    fetched_at: str
    parser_version: str
    confidence: float = 0.95
    cache_hit: bool = False


class ErrorModel(BaseModel):
    code: str
    message: str
    retryable: bool


class CandidateModel(BaseModel):
    title: str
    product_url: str
    price: dict[str, Any] | None = None
    matched: dict[str, Any] | None = None


class LookupResponse(BaseModel):
    request_id: str
    status: Literal["ok", "not_found", "ambiguous", "error"]
    supplier_id: str
    matched: MatchedModel | None = None
    price: PriceModel | None = None
    stock: StockModel | None = None
    meta: MetaModel | None = None
    candidates: list[CandidateModel] | None = None
    error: ErrorModel | None = None


class HealthResponse(BaseModel):
    status: str
    version: str


class SupplierPublic(BaseModel):
    id: str
    name: str
    enabled: bool


class SuppliersResponse(BaseModel):
    suppliers: list[SupplierPublic]
