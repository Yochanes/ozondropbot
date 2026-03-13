from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile

from ozondropbot.config import Config
from ozondropbot.db import Database
from ozondropbot.keyboards.common import add_product_keyboard
from ozondropbot.services.graph import build_price_history_plot
from ozondropbot.services.ozon import OzonParser, extract_ozon_id


def build_router(db: Database, config: Config, parser: OzonParser) -> Router:
    router = Router()

    @router.message(Command("start"))
    async def start_cmd(message: Message) -> None:
        await db.ensure_user(message.from_user.id)
        await message.answer(
            "Привет! Отправь ссылку Ozon, и я начну отслеживать цену.\n"
            "Бесплатно — до 10 товаров.\n"
            "Команды: /list /history <id> /drops /delete <id> /premium /settings",
            reply_markup=add_product_keyboard(),
        )

    @router.message(Command("premium"))
    async def premium_cmd(message: Message) -> None:
        await message.answer(
            "Premium: без лимита товаров, персональный порог и частота проверок, дроп-уведомления.\n"
            "Оплата: подключите ЮKassa / Telegram Stars в production-конфиге."
        )

    @router.message(Command("settings"))
    async def settings_cmd(message: Message) -> None:
        user = await db.get_user(message.from_user.id)
        if not user:
            await db.ensure_user(message.from_user.id)
            user = await db.get_user(message.from_user.id)
        if not user["premium_until"]:
            await message.answer("/settings доступно только Premium-пользователям.")
            return
        await message.answer(
            f"Текущие настройки:\n"
            f"- check_interval: {user['check_interval_minutes']} мин\n"
            f"- threshold: {user['drop_threshold_percent']}%\n"
            f"- timezone: {user['timezone']}\n"
            "Для изменения используйте админ/API слой (MVP)."
        )

    @router.message(Command("list"))
    async def list_cmd(message: Message) -> None:
        items = await db.list_user_products(message.from_user.id)
        if not items:
            await message.answer("Список пуст. Пришлите ссылку на товар Ozon.")
            return
        lines = ["Ваши товары:"]
        for row in items:
            delta = "n/a"
            if row.previous_price and row.current_price:
                pct = ((row.current_price - row.previous_price) / row.previous_price) * 100
                delta = f"{pct:+.2f}%"
            lines.append(f"• {row.title} [{row.ozon_id}] — {row.current_price or 'n/a'} ₽ ({delta})")
        await message.answer("\n".join(lines))

    @router.message(Command("delete"))
    async def delete_cmd(message: Message) -> None:
        parts = (message.text or "").split()
        if len(parts) < 2:
            await message.answer("Использование: /delete <ozon_id>")
            return
        ok = await db.delete_user_product(message.from_user.id, parts[1])
        await message.answer("Удалено." if ok else "Товар не найден в вашем списке.")

    @router.message(Command("history"))
    async def history_cmd(message: Message) -> None:
        parts = (message.text or "").split()
        if len(parts) < 2:
            await message.answer("Использование: /history <ozon_id>")
            return
        ozon_id = parts[1]
        items = await db.list_user_products(message.from_user.id)
        product = next((x for x in items if x.ozon_id == ozon_id), None)
        if not product:
            await message.answer("Товар не найден у вас в отслеживании.")
            return

        history = await db.get_price_history(product.product_id)
        if len(history) < 2:
            await message.answer("Недостаточно данных для графика. Подождите следующие проверки.")
            return

        image = build_price_history_plot(product.title, history)
        text_tail = "\n".join(
            f"{h['timestamp'][:19]} — {h['price']} ₽" for h in history[-10:]
        )
        await message.answer_photo(
            BufferedInputFile(image.read(), filename="history.png"),
            caption=f"История цены: {product.title}\n\nПоследние изменения:\n{text_tail}",
        )

    @router.message(Command("drops"))
    async def drops_cmd(message: Message) -> None:
        drops = await db.get_global_drops(config.drops_feed_threshold_percent, config.drops_feed_limit)
        if not drops:
            await message.answer("Пока нет свежих дропов ≥10%.")
            return
        lines = ["Топ дропов:"]
        for d in drops:
            lines.append(
                f"• {d['title']} — -{d['drop_percent']}% ({d['prev_price']}→{d['price']} ₽)\n{d['url']}"
            )
        await message.answer("\n".join(lines))

    @router.message(F.text)
    async def add_from_link(message: Message) -> None:
        text = (message.text or "").strip()
        if "ozon.ru" not in text:
            return
        await db.ensure_user(message.from_user.id)
        user = await db.get_user(message.from_user.id)
        count = await db.get_user_products_count(message.from_user.id)
        if not user["premium_until"] and count >= config.free_products_limit:
            await message.answer("Лимит free-тарифа: 10 товаров. Подключите /premium")
            return

        ozon_id = extract_ozon_id(text)
        if not ozon_id:
            await message.answer("Не смог распознать артикул в ссылке Ozon.")
            return

        snapshot = await parser.fetch_product(text)
        product_id = await db.add_product_for_user(
            message.from_user.id,
            snapshot.ozon_id,
            snapshot.url,
            snapshot.title,
        )
        await db.append_price(product_id, snapshot.current_price, snapshot.old_price, snapshot.promo)
        await message.answer(
            f"Добавил: {snapshot.title}\n"
            f"Текущая цена: {snapshot.current_price:.2f} ₽\n"
            f"Артикул: {snapshot.ozon_id}"
        )

    return router
