from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Клавиатура для /start — единственная кнопка «🔷 Главное меню»
start_kb = ReplyKeyboardMarkup(
    keyboard=[[ KeyboardButton(text="🔷 Главное меню") ]],
    resize_keyboard=True,
    one_time_keyboard=False,
)
# Главное меню
#tariff_kb = ReplyKeyboardMarkup(
#    keyboard=[
#        [
#            KeyboardButton(text="Купить/продлить VPN"),
#            KeyboardButton(text="Мой профиль"),
#        ],
#        [
#            KeyboardButton(text="📖 Инструкция"),
#            KeyboardButton(text="❓ Помощь"),
#        ],
#    ],
#    resize_keyboard=True,
#    one_time_keyboard=False,
#)

# Меню «Сроки подписки»
durations_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🟡 1 мес – 100₽"),
            KeyboardButton(text="🟢 2 мес – 200₽"),
        ],
        [
            KeyboardButton(text="🔵 3 мес – 300₽"),
            KeyboardButton(text="🔶 6 мес – 600₽"),
        ],
        [
            KeyboardButton(text="◀️ Назад"),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)

# Меню «Способы оплаты»
payment_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="💳 Перевод"),
            KeyboardButton(text="⭐️ Телеграм‑звезды"),
        ],
        [
            KeyboardButton(text="◀️ Назад"),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)

# Меню «Профиль»
profile_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🔑 Мои активные ключи"),
        ],
        [
            KeyboardButton(text="◀️ Назад"),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)
