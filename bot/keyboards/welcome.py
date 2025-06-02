from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import glv

# Тексты кнопок на русском
BTN_BUY_SUB_RU = "Купить подписку 🛒"
BTN_TRY_FREE_RU = "7 дней бесплатно 🚀"

def get_welcome_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=BTN_BUY_SUB_RU,
            callback_data="buy_subscription_action"
        )
    )
    if glv.config and glv.config.get('TEST_PERIOD'):
        builder.row(
            InlineKeyboardButton(
                text=BTN_TRY_FREE_RU,
                callback_data="try_free_action"
            )
        )
    return builder.as_markup() 