# Audit: kvadrat

| Поле | Значение |
|------|----------|
| supplier_id | kvadrat |
| name | КВАДРАТ |
| base_url | https://spkvadrat.ru/ |
| enabled | true |
| ассортимент | Фурнитура, электрика, плиты, кромка, компакт, ручки |

## Наблюдения

- Широкий каталог; стабильный live-парсинг без согласованных URL рискован.
- Whitelist snapshot: `KV-SLIDE-450`.

## Решение

`enabled: true` (snapshot). Расширение только через whitelist.
