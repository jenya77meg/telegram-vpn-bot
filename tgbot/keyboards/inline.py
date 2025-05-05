from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

# Inline‑клавиатура приветствия
builder = InlineKeyboardBuilder()
builder.button(text="Купить 🛒", callback_data="vpn")
builder.button(text="7 дней бесплатно", callback_data="free_trial_inline")
builder.adjust(2)
inline_start_kb = builder.as_markup()

# Inline‑клавиатура помощи
builder = InlineKeyboardBuilder()
builder.button(
    text="Клиенты для подключения",
    url="https://marzban-docs.sm1ky.com/start/reality_app/"
)
builder.adjust(1)
keyboard_help = builder.as_markup()

# Inline‑клавиатура отмены текущего действия
builder = InlineKeyboardBuilder()
builder.button(text="❌Выйти из меню", callback_data="cancel")
builder.adjust(1)
keyboard_cancel = builder.as_markup()