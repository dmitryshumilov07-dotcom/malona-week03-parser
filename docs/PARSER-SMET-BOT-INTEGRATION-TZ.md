# ТЗ: интеграция парсера цен с ботом-сметчиком

**Версия:** 1.0  
**Дата:** 2026-10-16  
**Аудитория:** разработчик парсера (backend / scraping)  
**Заказчик интеграции:** команда бота-сметчика  

---

## 1. Цель

При формировании сметы бот-сметчик запрашивает у сервиса парсера **актуальные цены с сайтов поставщиков** и подставляет их в строки сметы с указанием источника (URL, время снятия, поставщик).

Парсер **не** ведёт диалог с пользователем и **не** хранит бизнес-логику сметы — только снятие и нормализация цены по запросу.

---

## 2. Роли и границы ответственности

| Компонент | Ответственность |
|-----------|-----------------|
| **Бот-сметчик** | UI/диалог, позиции сметы, выбор поставщика, HTTP-вызов парсера, кэш/TTL, пересчёт итогов, отображение пользователю |
| **Сервис парсера** | Lookup по `supplier_id` + артикул/URL, возврат JSON (цена или структурированная ошибка) |
| **Инфра** | HTTPS, секреты, мониторинг, rate limit (согласовать URL staging/prod) |

---

## 3. Архитектура интеграции

Рекомендуемая схема: **синхронный HTTP JSON API** (фаза 2 — batch).

```text
Бот-сметчик  ──POST /v1/prices/lookup──►  Сервис парсера
              ◄── JSON (цена или error)──
```

- Транспорт: **HTTPS** (prod), **JSON**, UTF-8  
- `Content-Type: application/json; charset=utf-8`  
- Базовый URL и ключи выдаёт команда бота (отдельно staging / prod)

---

## 4. Аутентификация и лимиты

Согласовать один вариант и зафиксировать в env обеих сторон:

| Вариант | Заголовок |
|---------|-----------|
| A (рекомендуется) | `Authorization: Bearer <PARSER_API_KEY>` |
| B | `X-API-Key: <PARSER_API_KEY>` |

**Требования к парсеру:**

- `401` — неверный ключ (без лишних деталей в теле)
- `429` — превышен лимит + заголовок `Retry-After` (секунды)
- Документированные лимиты (пример): **60 req/min** на ключ, **≤5** параллельных lookup на один `supplier_id`

**Трассировка:** бот передаёт `X-Request-Id: <uuid>`; парсер возвращает тот же `request_id` в JSON (и желательно эхом в заголовке).

---

## 5. API

### 5.1. Поиск цены (основной метод)

**`POST /v1/prices/lookup`**

#### Запрос

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "supplier_id": "autodoc",
  "query": {
    "article": "OC90",
    "brand": "MAHLE",
    "name": "Фильтр масляный",
    "oem": null,
    "url": null
  },
  "options": {
    "need_stock": true,
    "currency": "RUB",
    "timeout_ms": 25000
  }
}
```

| Поле | Обяз. | Описание |
|------|-------|----------|
| `request_id` | да | UUID от бота (логи, идempotency) |
| `supplier_id` | да | Код из реестра поставщиков (§8) |
| `query.article` | * | Артикул |
| `query.brand` | нет | Бренд (уточнение при поиске) |
| `query.name` | нет | Наименование (логи / матчинг) |
| `query.oem` | нет | OEM при наличии |
| `query.url` | нет | Прямая ссылка на карточку — **приоритет** над поиском по артикулу |
| `options.need_stock` | нет | Нужно ли поле наличия |
| `options.currency` | нет | Ожидаемая валюта (`RUB`) |
| `options.timeout_ms` | нет | Макс. время работы (бот обычно ждёт ≤30 с) |

\* Обязательно хотя бы одно: `query.url` или `query.article`.

#### Успех — `200 OK`, `status: "ok"`

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ok",
  "supplier_id": "autodoc",
  "matched": {
    "article": "OC90",
    "brand": "MAHLE",
    "title": "Фильтр масляный MAHLE OC90",
    "product_url": "https://example.com/product/123"
  },
  "price": {
    "amount": 1245.0,
    "currency": "RUB",
    "vat_included": true,
    "price_type": "retail"
  },
  "stock": {
    "available": true,
    "quantity_text": "В наличии"
  },
  "meta": {
    "fetched_at": "2026-10-16T11:40:00Z",
    "parser_version": "1.2.3",
    "confidence": 0.95,
    "cache_hit": false
  }
}
```

| Поле | Правило |
|------|---------|
| `price.amount` | number; для RUB — до 2 знаков после запятой где применимо |
| `price_type` | `retail` \| `wholesale` \| `unknown` |
| `meta.fetched_at` | ISO 8601 UTC — **момент снятия с сайта поставщика** |
| `meta.confidence` | 0..1; при **< 0.85** бот может пометить строку «проверить вручную» |
| `matched.product_url` | Обязателен при `status=ok` |

#### Бизнес-результат без цены — `200 OK`

Предпочтительно не смешивать с HTTP 404 на уровне транспорта (согласовать с командой бота):

```json
{
  "request_id": "...",
  "status": "not_found",
  "supplier_id": "autodoc",
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "Нет карточки по article+brand",
    "retryable": false
  }
}
```

#### Несколько совпадений — `200 OK`, `status: "ambiguous"`

```json
{
  "request_id": "...",
  "status": "ambiguous",
  "supplier_id": "autodoc",
  "candidates": [
    {
      "title": "...",
      "product_url": "https://...",
      "price": { "amount": 1245.0, "currency": "RUB" },
      "matched": { "article": "OC90", "brand": "MAHLE" }
    }
  ],
  "error": {
    "code": "MULTIPLE_MATCHES",
    "message": "Выберите карточку",
    "retryable": false
  }
}
```

Не более **5** кандидатов в `candidates`.

#### HTTP-ошибки (транспорт / инфра)

| HTTP | Когда |
|------|--------|
| 400 | Невалидный JSON, нет `supplier_id`, нет `article` и `url` |
| 401 | Неверный API-ключ |
| 404 | Неизвестный `supplier_id` |
| 408 / 504 | Таймаут парсинга |
| 422 | Поставщик недоступен: captcha, блокировка, изменилась вёрстка |
| 429 | Rate limit |
| 500 | Внутренняя ошибка парсера |
| 503 | Обслуживание / деградация |

#### Коды `error.code` (минимальный набор)

| Код | `retryable` | Смысл |
|-----|-------------|--------|
| `PRODUCT_NOT_FOUND` | false | Карточка не найдена |
| `MULTIPLE_MATCHES` | false | Нужен выбор пользователя (`candidates`) |
| `SUPPLIER_BLOCKED` | true | 403 / captcha / anti-bot |
| `SUPPLIER_TIMEOUT` | true | Сайт не ответил в срок |
| `PARSE_ERROR` | false* | Не удалось извлечь цену (вёрстка) |
| `RATE_LIMITED` | true | Лимит парсера или сайта |

\* `PARSE_ERROR` может быть `retryable: true`, если команда бота договорится о повторе позже.

У каждой ошибки в теле: **`retryable`: boolean**.

---

### 5.2. Пакетный запрос (фаза 2, опционально)

**`POST /v1/prices/lookup/batch`**

```json
{
  "request_id": "...",
  "items": [
    { "line_id": "1", "supplier_id": "autodoc", "query": { "article": "OC90", "brand": "MAHLE" } },
    { "line_id": "2", "supplier_id": "exist", "query": { "article": "W712/75", "brand": "MANN" } }
  ],
  "options": { "max_parallel": 3, "timeout_ms": 60000 }
}
```

Ответ: массив объектов с тем же `line_id` и тем же форматом, что у одиночного lookup. **Ошибка одной строки не отменяет остальные.**

---

### 5.3. Служебные методы (обязательны для prod)

**`GET /v1/health`**

```json
{ "status": "ok", "version": "1.2.3" }
```

**`GET /v1/suppliers`**

```json
{
  "suppliers": [
    { "id": "autodoc", "name": "Autodoc", "enabled": true },
    { "id": "exist", "name": "Exist.ru", "enabled": true }
  ]
}
```

Бот использует список для UI и валидации `supplier_id` до lookup.

---

## 6. Поведение бота-сметчика (контекст для парсера)

1. Lookup вызывается **на строку сметы**, где выбран источник «цена с сайта поставщика».
2. В смете сохраняются: `amount`, `currency`, `product_url`, `fetched_at`, `supplier_id`, `request_id`, при необходимости `confidence`.
3. Повторный запрос может не выполняться, если **TTL кэша** на стороне бота не истёк (типично 6–24 ч).
4. Если парсер отдаёт кэш, поле `meta.cache_hit: true`; **`fetched_at`** — время реального снятия с сайта (не время HTTP-запроса бота). При необходимости добавить `meta.cached_at`.
5. При `status: ambiguous` бот показывает `candidates` пользователю; повторный lookup может идти с `query.url` выбранной карточки.
6. Бот **не** передаёт парсеру логины пользователей; учётные данные B2B-порталов — только в secure-хранилище парсера.

---

## 7. Маппинг ответа парсера → строка сметы (для согласования)

| Поле сметы (бот) | Поле ответа парсера |
|------------------|---------------------|
| `unit_price` | `price.amount` |
| `currency` | `price.currency` |
| `supplier_id` | `supplier_id` |
| `source_url` | `matched.product_url` |
| `price_fetched_at` | `meta.fetched_at` |
| `price_confidence` | `meta.confidence` |
| `stock_status` | `stock.available` / `stock.quantity_text` |
| `line_note` | при `confidence < 0.85` — «проверить цену вручную» |

Точные имена полей в модели сметы бота уточняются командой бота; парсер **не меняет** схему сметы.

---

## 8. Реестр поставщиков

Общий артефакт (репозиторий парсера или общий config):

```yaml
suppliers:
  - id: autodoc
    name: Autodoc
    base_url: https://www.autodoc.ru
    enabled: true
    parser_module: autodoc
  - id: exist
    name: Exist.ru
    base_url: https://exist.ru
    enabled: true
    parser_module: exist
```

**Правило:** значение `supplier_id` в API **строго** из реестра. Новый поставщик = запись в реестре + адаптер + обновление `GET /v1/suppliers` + уведомление команды бота.

---

## 9. Нефункциональные требования

| Параметр | Целевое значение (согласовать) |
|----------|----------------------------------|
| p95 latency `lookup` | ≤15 с (HTTP/HTML), ≤25 с (headless) |
| Доступность | 99% в рабочие часы |
| Логи | `request_id`, `supplier_id`, article/url, `duration_ms`, `status`; без PII |
| Идempotency | Повтор с тем же `request_id` в течение 5 мин — тот же результат или явный `cache_hit` |
| Версионирование | Префикс `/v1/`; breaking changes — только `/v2/` |

---

## 10. Безопасность

- Prod: только HTTPS.
- API-ключ не в query string.
- Опционально: allowlist IP сервера бота-сметчика.
- Не писать в prod-логи полный HTML; для отладки — hash страницы + усечённый фрагмент по feature-flag.

---

## 11. Приёмка и артефакты от разработчика парсера

Перед подключением prod бота:

1. **OpenAPI 3** (`openapi.yaml`) для `/v1/prices/lookup`, `/v1/health`, `/v1/suppliers`.
2. **Staging:** base URL + тестовый API-ключ.
3. **Набор тест-кейсов:** ≥10 на поставщика (запрос JSON → ожидаемый `status` + эталонные ответы).
4. Кейсы ошибок: неверный артикул, timeout, `MULTIPLE_MATCHES`.
5. Совместный прогон: бот на staging, минимум 3 артикула × 2 поставщика → `status=ok` с `amount`, `product_url`, `fetched_at` в рамках SLA.

**Критерий приёмки:** бот успешно заполняет строки сметы реальными ценами с указанием ссылки и времени снятия.

---

## 12. Чеклист разработчика парсера

- [ ] HTTP-сервис: `POST /v1/prices/lookup`, `GET /v1/health`, `GET /v1/suppliers`
- [ ] Адаптеры согласованных `supplier_id`
- [ ] Единый JSON-контракт и коды `error.code`
- [ ] Проброс `request_id` в логи и ответ
- [ ] Auth + rate limit + `429` / `Retry-After`
- [ ] OpenAPI + примеры `curl` для команды бота
- [ ] Staging для интеграционных тестов
- [ ] (Фаза 2) `POST /v1/prices/lookup/batch`

---

## 13. Открытые вопросы (созвон)

1. Base URL staging / prod парсера.
2. Auth: Bearer vs `X-API-Key`.
3. `not_found`: всегда `200` + `status` vs HTTP 404.
4. TTL кэша и семантика `fetched_at` / `cache_hit` / `cached_at`.
5. Список `supplier_id` для v1 и приоритет разработки адаптеров.
6. Нужен ли batch в первой версии.

---

## 14. История изменений

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | 2026-10-16 | Первоначальная версия ТЗ |
