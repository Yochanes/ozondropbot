from __future__ import annotations

import asyncio
import structlog
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from ozondropbot.config import Config
from ozondropbot.db import Database
from ozondropbot.handlers.commands import build_router
from ozondropbot.scheduler import setup_scheduler
from ozondropbot.services.ozon import OzonParser


async def run() -> None:
    load_dotenv()
    config = Config.from_env()

    structlog.configure()
    log = structlog.get_logger(__name__)

    bot = Bot(token=config.bot_token)
    dp = Dispatcher()

    db = Database(config.database_path)
    await db.init()

    parser = OzonParser()
    dp.include_router(build_router(db, config, parser))
    setup_scheduler(bot, db, parser, config)

    log.info("bot_started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run())
