# Дизайн адаптеров парсера

## Поток

```text
app.py → suppliers.yaml → ADAPTERS[parser_module]
  → BaseAdapter.lookup()
       whitelist → HTML (snapshot|live) → price / error codes
```

## Модули (из ПОСТАВЩИКИ.xlsx)

| parser_module | supplier_id | Состояние |
|---------------|-------------|-----------|
| `blum` | blum | ok / not_found / ambiguous |
| `mdm_complect` | mdm-complect | ok / not_found (+ captcha live) |
| `kvadrat` | kvadrat | ok / not_found |
| `boyard` | boyard | ok / not_found |
| `dinastiya` | dinastiya | disabled |
| `makmart` | makmart | disabled |
| `nt74` | nt-74 | disabled / stub |

## Правила

- только whitelist `fixtures/suppliers_test_queries.yaml`;
- пауза ≥ 2 с на поставщика; 60 req/min; ≤5 parallel;
- captcha → `SUPPLIER_BLOCKED`, без обхода;
- секреты только в `.env`.
