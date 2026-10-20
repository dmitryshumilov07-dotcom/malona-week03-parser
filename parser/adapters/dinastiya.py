from __future__ import annotations

from parser.adapters.base import BaseAdapter, LookupResult
from parser.models import ErrorModel, LookupRequest


class DinastiyaAdapter(BaseAdapter):
    supplier_id = "dinastiya"

    def _lookup_impl(self, req: LookupRequest) -> LookupResult:
        return LookupResult(
            status="error",
            error=ErrorModel(
                code="SUPPLIER_BLOCKED",
                message="Династия отключена в suppliers.yaml (stub / нет whitelist)",
                retryable=True,
            ),
            http_status=422,
        )
