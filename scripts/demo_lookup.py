#!/usr/bin/env python3
"""Run 3+ ok lookups + print mapping table."""
from __future__ import annotations

import json
import os
import time
import uuid

import httpx

BASE = os.getenv("PARSER_BASE", "http://127.0.0.1:8000")
KEY = os.getenv("PARSER_API_KEY", "dev-parser-key-change-me")

CALLS = [
    {
        "supplier_id": "blum",
        "query": {
            "article": "71B3550",
            "brand": "BLUM",
            "url": "https://blum-msk.ru/catalog/demo/71b3550",
        },
    },
    {
        "supplier_id": "kvadrat",
        "query": {
            "article": "KV-SLIDE-450",
            "brand": "KVADRAT",
            "url": "https://spkvadrat.ru/catalog/demo/kv-slide-450",
        },
    },
    {
        "supplier_id": "boyard",
        "query": {
            "article": "BOYARD-H300",
            "brand": "BOYARD",
            "url": "https://boyard-chel.biz/catalog/demo/boyard-h300",
        },
    },
]


def main() -> None:
    headers = {
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
    }
    print("GET /v1/health", httpx.get(f"{BASE}/v1/health").json())
    print("GET /v1/suppliers", httpx.get(f"{BASE}/v1/suppliers", headers=headers).json())
    print()
    rows = []
    for call in CALLS:
        body = {
            "request_id": str(uuid.uuid4()),
            "supplier_id": call["supplier_id"],
            "query": call["query"],
            "options": {"need_stock": True, "currency": "RUB"},
        }
        time.sleep(2.1)  # pause between suppliers not required, but safe vs same-id retries
        r = httpx.post(f"{BASE}/v1/prices/lookup", headers=headers, json=body, timeout=30)
        data = r.json()
        print(f"=== {call['supplier_id']} HTTP {r.status_code} ===")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        if data.get("status") == "ok":
            rows.append(
                {
                    "unit_price": data["price"]["amount"],
                    "currency": data["price"]["currency"],
                    "supplier_id": data["supplier_id"],
                    "source_url": data["matched"]["product_url"],
                    "price_fetched_at": data["meta"]["fetched_at"],
                    "price_confidence": data["meta"]["confidence"],
                }
            )
    print("\n=== estimate line mapping ===")
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"\nok_count={len(rows)}")


if __name__ == "__main__":
    main()
