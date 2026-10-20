from __future__ import annotations

from parser.adapters.base import BaseAdapter, LookupResult
from parser.models import ErrorModel, LookupRequest


class Nt74Adapter(BaseAdapter):
    supplier_id = "nt-74"

    def _lookup_impl(self, req: LookupRequest) -> LookupResult:
        return LookupResult(
            status="error",
            error=ErrorModel(
                code="PARSE_ERROR",
                message="Адаптер Новые Технологии не реализован (audit only)",
                retryable=False,
            ),
            http_status=422,
        )
