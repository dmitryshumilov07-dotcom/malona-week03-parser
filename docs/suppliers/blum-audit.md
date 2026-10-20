# Audit: blum

| Поле | Значение |
|------|----------|
| supplier_id | blum |
| name | BLUM |
| base_url | https://blum-msk.ru/ |
| enabled | true |
| ассортимент | Петли, системы выдвижения, направляющие, подъёмные механизмы |

## Наблюдения

- Официальный сайт дилера/каталога BLUM.
- Карточки часто под JS/антиботом; для сдачи недели 3 — whitelist + HTML snapshot артикула `71B3550`.
- Адаптер: `ok` / `not_found` / `ambiguous`.

## Решение

`enabled: true`. Captcha не обходим; при live-блоке — `SUPPLIER_BLOCKED`.
