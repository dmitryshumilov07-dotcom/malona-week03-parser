from __future__ import annotations

from parser.adapters.base import BaseAdapter, LookupResult
from parser.models import ErrorModel, LookupRequest


class MakmartAdapter(BaseAdapter):
    supplier_id = "makmart"

    def _lookup_impl(self, req: LookupRequest) -> LookupResult:
        return LookupResult(
            status="error",
            error=ErrorModel(
                code="SUPPLIER_BLOCKED",
                message="МакМарт отключён (anti-bot риск / адаптер не готов)",
                retryable=True,
            ),
            http_status=422,
        )
