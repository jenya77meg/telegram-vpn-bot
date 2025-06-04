from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup,  WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_pay_keyboard(url) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Оплатить 💳",
            url=url
        )
    )
    return builder.as_markup()
