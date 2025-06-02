from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

import glv

# Текст кнопки на русском
TEXT_FOLLOW_LINK_RU = "Перейти 🔗"

def get_subscription_keyboard(subscription_url) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=TEXT_FOLLOW_LINK_RU,
            url=subscription_url
        )
    )
    return builder.as_markup()