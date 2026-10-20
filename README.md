# Неделя 3 — парсер цен + интеграция с ботом-сметчиком

ТЗ: `docs/PARSER-SMET-BOT-INTEGRATION-TZ.md`  
Поставщики: `docs/ПОСТАВЩИКИ.xlsx` (источник: `postavshchiki.xlsx`)

## Поставщики (xlsx → yaml)

| id | name | enabled |
|----|------|---------|
| blum | BLUM | true |
| mdm-complect | МДМ | false (live captcha) |
| kvadrat | КВАДРАТ | true |
| boyard | Боярд | true |
| dinastiya | Династия | false |
| makmart | МакМарт | false |
| nt-74 | Новые Технологии | false |

## Старт

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn parser.app:app --host 127.0.0.1 --port 8000
```

```bash
pytest -q
python scripts/demo_lookup.py
```

Live MDM часто отдаёт captcha — обход запрещён. Демо `status: ok` на whitelist + HTML snapshots (`PARSER_USE_PAGE_SNAPSHOTS=1`).
