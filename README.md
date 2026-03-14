# OzonDropBot

Telegram-бот для отслеживания цен на Ozon с историей, графиками и детектом дропов.

## Что реализовано (MVP)

- Добавление товара отправкой Ozon-ссылки.
- Хранение пользователей, товаров, подписок и истории цен в SQLite.
- Команды: `/start`, `/list`, `/history <ozon_id>`, `/drops`, `/premium`, `/delete <ozon_id>`, `/settings`.
- Планировщик APScheduler для периодических проверок.
- Уведомления о дропах только для premium-пользователей.
- Генерация графика цены через matplotlib/seaborn.

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
export BOT_TOKEN=123:abc
python -m ozondropbot.main
```

## Совместимость со старыми CPU

Если у вас старый процессор (например, AMD Phenom II) и возникает ошибка `illegal hardware instruction python`, установите зависимости из `requirements.txt` (там зафиксированы более совместимые версии `numpy`, `matplotlib`, `seaborn`, `structlog`).

```bash
pip install -r requirements.txt
```

## Структура

- `src/ozondropbot/main.py` — запуск бота.
- `src/ozondropbot/db.py` — SQLite-слой.
- `src/ozondropbot/handlers/commands.py` — команды и добавление по ссылке.
- `src/ozondropbot/scheduler.py` — фоновые проверки.
- `src/ozondropbot/services/graph.py` — графики истории.
- `src/ozondropbot/services/ozon.py` — распознавание артикула + поставщик снапшота.

## Production notes

Для production нужно заменить `OzonParser.fetch_product` на Playwright+proxy реализацию и подключить платежный шлюз (ЮKassa/Telegram Stars).
