# Как бот-сметчик вызывает парсер

## Схема

```text
Пользователь → Бот-сметчик → POST /v1/prices/lookup → Сервис парсера
                              ← JSON (ok / not_found / ambiguous / error)
                 ↓
            строка сметы (unit_price, source_url, …)
```

Парсер **не** ведёт диалог и **не** хранит смету.

## Auth

```http
Authorization: Bearer <PARSER_API_KEY>
Content-Type: application/json; charset=utf-8
X-Request-Id: <uuid>
```

## Пример запроса (поставщик из ПОСТАВЩИКИ.xlsx)

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "supplier_id": "blum",
  "query": {
    "article": "71B3550",
    "brand": "BLUM",
    "url": "https://blum-msk.ru/catalog/demo/71b3550"
  },
  "options": { "need_stock": true, "currency": "RUB", "timeout_ms": 25000 }
}
```

## Поведение бота по `status`

| status | Действие бота |
|--------|----------------|
| `ok` | Заполнить цену и источник; при `confidence < 0.85` — «проверить вручную» |
| `not_found` | Другой поставщик / URL |
| `ambiguous` | Показать `candidates`; повтор с `query.url` |
| `error` + `retryable` | Повторить позже / отключить поставщика |

## Маппинг → строка сметы

| Поле сметы | Поле ответа парсера |
|------------|---------------------|
| `unit_price` | `price.amount` |
| `currency` | `price.currency` |
| `supplier_id` | `supplier_id` |
| `source_url` | `matched.product_url` |
| `price_fetched_at` | `meta.fetched_at` |
| `price_confidence` | `meta.confidence` |
| `stock_status` | `stock.available` / `stock.quantity_text` |
| `line_note` | при `confidence < 0.85` — «проверить цену вручную» |
| `parser_request_id` | `request_id` |

Реестр `supplier_id`: `blum`, `mdm-complect`, `kvadrat`, `boyard`, `dinastiya`, `makmart`, `nt-74`.
