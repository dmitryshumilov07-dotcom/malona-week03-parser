from __future__ import annotations

import logging
import time
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from parser import __version__
from parser.adapters import ADAPTERS
from parser.models import (
    ErrorModel,
    HealthResponse,
    LookupRequest,
    LookupResponse,
    SupplierPublic,
    SuppliersResponse,
)
from parser.rate_limit import RateLimiter
from parser.registry import load_suppliers
from parser.settings import get_settings

logger = logging.getLogger("parser")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

settings = get_settings()
limiter = RateLimiter(
    per_min=settings.parser_rate_limit_per_min,
    supplier_pause_sec=settings.parser_supplier_pause_sec,
    max_parallel=settings.parser_max_parallel_per_supplier,
)

# Idempotency: request_id -> (expires_at, response_dict, http_status)
_idem: dict[str, tuple[float, dict, int]] = {}

app = FastAPI(
    title="Supplier Price Parser",
    version=settings.parser_version,
    description="HTTP JSON API для бота-сметчика (неделя 3)",
)


def require_bearer(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.parser_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return token


@app.get("/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=settings.parser_version or __version__)


@app.get("/v1/suppliers", response_model=SuppliersResponse)
def suppliers(_: Annotated[str, Depends(require_bearer)]) -> SuppliersResponse:
    items = [
        SupplierPublic(id=s.id, name=s.name, enabled=s.enabled)
        for s in load_suppliers().values()
    ]
    return SuppliersResponse(suppliers=items)


@app.post("/v1/prices/lookup", response_model=LookupResponse)
def prices_lookup(
    body: LookupRequest,
    response: Response,
    request: Request,
    api_key: Annotated[str, Depends(require_bearer)],
    x_request_id: Annotated[str | None, Header()] = None,
) -> LookupResponse | JSONResponse:
    # Echo tracing header
    rid = body.request_id or x_request_id
    if rid:
        response.headers["X-Request-Id"] = rid

    allowed, retry_after = limiter.check_key(api_key)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(retry_after), "X-Request-Id": body.request_id},
        )

    # Idempotency window 5 minutes
    now = time.time()
    cached = _idem.get(body.request_id)
    if cached and cached[0] > now:
        payload, status = cached[1], cached[2]
        response.headers["X-Request-Id"] = body.request_id
        if status != 200:
            return JSONResponse(status_code=status, content=payload, headers={"X-Request-Id": body.request_id})
        # mark cache_hit if ok
        if payload.get("status") == "ok" and payload.get("meta"):
            payload = {**payload, "meta": {**payload["meta"], "cache_hit": True}}
        return LookupResponse.model_validate(payload)

    suppliers = load_suppliers()
    cfg = suppliers.get(body.supplier_id)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Unknown supplier_id")

    if not cfg.enabled:
        payload = LookupResponse(
            request_id=body.request_id,
            status="error",
            supplier_id=body.supplier_id,
            error=ErrorModel(
                code="SUPPLIER_BLOCKED",
                message=cfg.disabled_reason or "Поставщик отключён в suppliers.yaml",
                retryable=True,
            ),
        ).model_dump()
        _idem[body.request_id] = (now + 300, payload, 422)
        return JSONResponse(status_code=422, content=payload, headers={"X-Request-Id": body.request_id})

    module = cfg.parser_module
    adapter_cls = ADAPTERS.get(module)
    if adapter_cls is None:
        raise HTTPException(status_code=500, detail="Adapter not registered")

    # Supplier concurrency / pause
    deadline = time.time() + max(1.0, body.options.timeout_ms / 1000.0)
    while True:
        ok, wait = limiter.acquire_supplier(body.supplier_id)
        if ok:
            break
        if time.time() + wait > deadline:
            payload = LookupResponse(
                request_id=body.request_id,
                status="error",
                supplier_id=body.supplier_id,
                error=ErrorModel(
                    code="RATE_LIMITED",
                    message="Превышен лимит параллельных lookup на поставщика",
                    retryable=True,
                ),
            ).model_dump()
            return JSONResponse(
                status_code=429,
                content=payload,
                headers={"Retry-After": str(int(wait) + 1), "X-Request-Id": body.request_id},
            )
        time.sleep(min(wait, 0.5))

    t0 = time.time()
    try:
        adapter = adapter_cls()
        result = adapter.lookup(body)
    finally:
        limiter.release_supplier(body.supplier_id)

    duration_ms = int((time.time() - t0) * 1000)
    logger.info(
        "lookup request_id=%s supplier_id=%s article=%s url=%s duration_ms=%s status=%s",
        body.request_id,
        body.supplier_id,
        body.query.article,
        body.query.url,
        duration_ms,
        result.status,
    )

    http_status = 200
    if result.status == "error" and result.error:
        code = result.error.code
        if code == "SUPPLIER_TIMEOUT":
            http_status = 504
        elif code in {"SUPPLIER_BLOCKED", "PARSE_ERROR"}:
            http_status = 422
        elif code == "RATE_LIMITED":
            http_status = 429

    payload = result.model_dump()
    _idem[body.request_id] = (now + 300, payload, http_status)

    if http_status != 200:
        return JSONResponse(
            status_code=http_status,
            content=payload,
            headers={"X-Request-Id": body.request_id},
        )
    return result


@app.exception_handler(ValidationError)
async def validation_exception_handler(_: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": exc.errors()})
