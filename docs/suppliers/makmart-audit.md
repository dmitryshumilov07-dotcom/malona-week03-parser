# Audit: makmart

| Поле | Значение |
|------|----------|
| supplier_id | makmart |
| name | МакМарт |
| base_url | https://makmart.ru/ |
| enabled | false |
| ассортимент | Фурнитура (системы выдвижения / направляющие / подъёмные) |

## Решение

`enabled: false` из‑за риска anti-bot и отсутствия согласованного whitelist. Отказ дешевле нестабильного парсера.
