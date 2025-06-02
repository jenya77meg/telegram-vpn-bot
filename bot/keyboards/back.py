from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
# Удаляем импорт gettext
# from aiogram.utils.i18n import gettext as _

# Текст кнопки на русском
TEXT_BACK_RU = "⏪ Назад"

def get_back_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [
            KeyboardButton(text=TEXT_BACK_RU), # Используем русскую строку
        ]
    ]
    
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
