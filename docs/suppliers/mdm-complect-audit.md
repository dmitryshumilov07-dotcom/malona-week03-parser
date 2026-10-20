# Audit: mdm-complect

| Поле | Значение |
|------|----------|
| supplier_id | mdm-complect |
| name | МДМ |
| base_url | https://www.mdm-complect.ru/ |
| enabled | true |
| ассортимент | Фурнитура, ручки, электрика, алюминиевые профиля |

## Наблюдения

- Live отвечает challenge «Are you not a robot?» → captcha / anti-bot.
- Обход captcha запрещён правилами недели.
- Для контракта API — snapshot whitelist URL demo-product-001.

## Решение

По правилам недели при captcha: **`enabled: false`** + `disabled_reason` в yaml.  
Адаптер и snapshot сохранены для локального разбора (`PARSER_USE_PAGE_SNAPSHOTS`), но API при `enabled: false` отдаёт `422 SUPPLIER_BLOCKED` до вызова адаптера.
