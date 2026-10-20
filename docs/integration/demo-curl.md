# Demo: curl + маппинг в смету

```bash
set PARSER_API_KEY=dev-parser-key-change-me
uvicorn parser.app:app --host 127.0.0.1 --port 8000
```

## health / suppliers

```bash
curl -sS "http://127.0.0.1:8000/v1/health"
curl -sS "http://127.0.0.1:8000/v1/suppliers" -H "Authorization: Bearer %PARSER_API_KEY%"
```

## 3+ lookup ok

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/prices/lookup" -H "Authorization: Bearer %PARSER_API_KEY%" -H "Content-Type: application/json" -d "{\"request_id\":\"11111111-1111-1111-1111-111111111111\",\"supplier_id\":\"blum\",\"query\":{\"article\":\"71B3550\",\"brand\":\"BLUM\",\"url\":\"https://blum-msk.ru/catalog/demo/71b3550\"},\"options\":{\"currency\":\"RUB\"}}"

curl -sS -X POST "http://127.0.0.1:8000/v1/prices/lookup" -H "Authorization: Bearer %PARSER_API_KEY%" -H "Content-Type: application/json" -d "{\"request_id\":\"22222222-2222-2222-2222-222222222222\",\"supplier_id\":\"kvadrat\",\"query\":{\"article\":\"KV-SLIDE-450\",\"brand\":\"KVADRAT\",\"url\":\"https://spkvadrat.ru/catalog/demo/kv-slide-450\"},\"options\":{\"currency\":\"RUB\"}}"

curl -sS -X POST "http://127.0.0.1:8000/v1/prices/lookup" -H "Authorization: Bearer %PARSER_API_KEY%" -H "Content-Type: application/json" -d "{\"request_id\":\"33333333-3333-3333-3333-333333333333\",\"supplier_id\":\"boyard\",\"query\":{\"article\":\"BOYARD-H300\",\"brand\":\"BOYARD\",\"url\":\"https://boyard-chel.biz/catalog/demo/boyard-h300\"},\"options\":{\"currency\":\"RUB\"}}"
```

Или: `python scripts/demo_lookup.py`

> `mdm-complect` в API отключён (`enabled: false`) из‑за live captcha.


## Маппинг ответа → смета

| Поле сметы | Откуда | Пример (BLUM) |
|------------|--------|----------------|
| `unit_price` | `price.amount` | `312.0` |
| `currency` | `price.currency` | `RUB` |
| `supplier_id` | `supplier_id` | `blum` |
| `source_url` | `matched.product_url` | `https://blum-msk.ru/catalog/demo/71b3550` |
| `price_fetched_at` | `meta.fetched_at` | ISO UTC |
| `price_confidence` | `meta.confidence` | `0.95` |

Демо на HTML-snapshots (`PARSER_USE_PAGE_SNAPSHOTS=1`): live MDM часто captcha, обход запрещён.
