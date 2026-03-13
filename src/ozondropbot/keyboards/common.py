from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def add_product_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Добавить товар", callback_data="add_product")]]
    )
