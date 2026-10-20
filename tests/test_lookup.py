from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from parser.app import app
from parser.registry import load_suppliers
from parser.settings import get_settings
from parser.whitelist import load_whitelist

CASES = json.loads((Path(__file__).parent / "lookup_cases.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def client(monkeypatch_module=None):
    import os

    os.environ.setdefault("PARSER_SUPPLIER_PAUSE_SEC", "0.01")
    os.environ.setdefault("PARSER_USE_PAGE_SNAPSHOTS", "1")
    get_settings.cache_clear()
    load_suppliers.cache_clear()
    load_whitelist.cache_clear()
    # refresh module-level limiter pause via settings used at import — recreate limiter lightly
    from parser import app as app_module
    from parser.rate_limit import RateLimiter

    s = get_settings()
    app_module.limiter = RateLimiter(
        per_min=s.parser_rate_limit_per_min,
        supplier_pause_sec=s.parser_supplier_pause_sec,
        max_parallel=s.parser_max_parallel_per_supplier,
    )
    with TestClient(app) as c:
        yield c


def _auth_header(enabled: bool = True) -> dict[str, str]:
    if not enabled:
        return {}
    return {"Authorization": f"Bearer {get_settings().parser_api_key}"}


def test_health(client: TestClient):
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_suppliers_from_xlsx(client: TestClient):
    r = client.get("/v1/suppliers", headers=_auth_header())
    assert r.status_code == 200
    ids = {s["id"] for s in r.json()["suppliers"]}
    assert ids == {
        "blum",
        "mdm-complect",
        "kvadrat",
        "boyard",
        "dinastiya",
        "makmart",
        "nt-74",
    }


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_lookup_cases(client: TestClient, case: dict):
    time.sleep(0.05)
    headers = _auth_header(case.get("auth", True))
    body = dict(case["request"])
    body["request_id"] = f"{body['request_id']}-{time.time_ns()}"
    r = client.post("/v1/prices/lookup", headers=headers, json=body)
    exp = case["expect"]
    assert r.status_code == exp["http_status"], r.text
    if "status" in exp:
        data = r.json()
        assert data["status"] == exp["status"]
        if exp.get("error_code"):
            assert data.get("error", {}).get("code") == exp["error_code"]
        if exp.get("price_min"):
            assert data["price"]["amount"] >= exp["price_min"]
            assert data["matched"]["product_url"]
            assert data["meta"]["fetched_at"]


def test_three_ok_lookups(client: TestClient):
    payloads = [
        {
            "request_id": f"ok-1-{time.time_ns()}",
            "supplier_id": "blum",
            "query": {
                "article": "71B3550",
                "brand": "BLUM",
                "url": "https://blum-msk.ru/catalog/demo/71b3550",
            },
            "options": {"currency": "RUB"},
        },
        {
            "request_id": f"ok-2-{time.time_ns()}",
            "supplier_id": "kvadrat",
            "query": {
                "article": "KV-SLIDE-450",
                "brand": "KVADRAT",
                "url": "https://spkvadrat.ru/catalog/demo/kv-slide-450",
            },
            "options": {"currency": "RUB"},
        },
        {
            "request_id": f"ok-3-{time.time_ns()}",
            "supplier_id": "boyard",
            "query": {
                "article": "BOYARD-H300",
                "brand": "BOYARD",
                "url": "https://boyard-chel.biz/catalog/demo/boyard-h300",
            },
            "options": {"currency": "RUB"},
        },
    ]
    headers = _auth_header()
    for p in payloads:
        time.sleep(0.1)
        r = client.post("/v1/prices/lookup", headers=headers, json=p)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "ok"
        assert data["price"]["amount"] > 0
