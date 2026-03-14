from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ozondropbot.config import Config
from ozondropbot.db import Database
from ozondropbot.services.drops import drop_percent
from ozondropbot.services.ozon import OzonParser


async def check_prices_once(bot: Bot, db: Database, parser: OzonParser, config: Config) -> None:
    rows = await db.iter_tracking_rows()
    for row in rows:
        snapshot = await parser.fetch_product(row["url"])
        old = row["current_price"]
        await db.append_price(row["product_id"], snapshot.current_price, snapshot.old_price, snapshot.promo)

        if old is None:
            continue
        pct = drop_percent(old, snapshot.current_price)
        if pct < config.default_drop_threshold_percent:
            continue

        premium_until = row.get("premium_until")
        premium_ok = False
        if premium_until:
            try:
                premium_ok = datetime.fromisoformat(premium_until) > datetime.now(timezone.utc)
            except ValueError:
                premium_ok = False

        if premium_ok:
            await bot.send_message(
                row["tg_id"],
                f"⚡ Дроп {pct:.2f}%!\n{row['title']}\n{old:.2f} → {snapshot.current_price:.2f} ₽\n{row['url']}",
            )


def setup_scheduler(bot: Bot, db: Database, parser: OzonParser, config: Config) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        check_prices_once,
        "interval",
        minutes=config.default_check_interval_minutes,
        args=[bot, db, parser, config],
        id="price-check",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
