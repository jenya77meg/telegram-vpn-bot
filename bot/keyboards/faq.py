from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Тексты для кнопок (короткие формулировки вопросов)
FAQ_Q1_BUTTON_TEXT = "Как получить тест?"
FAQ_Q2_BUTTON_TEXT = "Где использовать VPN?"
FAQ_Q3_BUTTON_TEXT = "Тарифы и цены?"
FAQ_Q4_BUTTON_TEXT = "Статус подписки?"
FAQ_Q5_BUTTON_TEXT = "Ограничения (трафик/скорость)?"
FAQ_Q6_BUTTON_TEXT = "Проблемы/Вопросы?"
FAQ_Q7_BUTTON_TEXT = "Что такое VPN? Это безопасно?" # Новый вопрос 7
FAQ_Q8_BUTTON_TEXT = "Какие приложения поддерживаются?" # Новый вопрос 8
TEXT_BACK_TO_MAIN_MENU_FAQ = "⏪ В главное меню" # Отдельная кнопка назад для FAQ

# Callback data для кнопок
FAQ_Q1_CALLBACK = "faq_q1"
FAQ_Q2_CALLBACK = "faq_q2"
FAQ_Q3_CALLBACK = "faq_q3"
FAQ_Q4_CALLBACK = "faq_q4"
FAQ_Q5_CALLBACK = "faq_q5"
FAQ_Q6_CALLBACK = "faq_q6"
FAQ_Q7_CALLBACK = "faq_q7" # Новый callback 7
FAQ_Q8_CALLBACK = "faq_q8" # Новый callback 8
# Для кнопки "Назад" будем использовать существующий обработчик текстовой кнопки "⏪ Назад",
# но для инлайн клавиатуры нам нужен другой callback или другой подход.
# Пока что сделаем для нее отдельный callback, например, "faq_back_to_main"
# или лучше, если такая кнопка уже где-то используется и ведет в главное меню,
# можно использовать тот же callback.
# Давайте пока сделаем ее просто callback 'show_main_menu'
# или даже лучше, если "Назад" тут означает назад к обычному меню,
# то она должна отправлять текстовую команду "Назад".
# Поскольку это Inline-клавиатура, "Назад" не может просто отправить текст как Reply кнопка.
# Самый простой способ - иметь отдельный callback для этой кнопки, который вернет главное меню.
# Или, если у нас есть callback "main_menu" для такой цели.
# Пусть будет 'faq_back_to_main' и мы его обработаем.
# Альтернативно, мы можем ее не добавлять сюда, а пользователь нажмет системную "Назад"
# или reply-кнопку "Назад", если она видна.
# Для консистентности с get_back_keyboard(), который обычно предлагает одну кнопку "Назад",
# здесь мы можем сделать кнопку "В главное меню", которая будет действовать как /start.
# Для этого мы можем использовать callback, который вызывает /start или его логику.
# Допустим, "go_start_from_faq"
CALLBACK_GO_START_FROM_FAQ = "go_start_from_faq"


def get_faq_questions_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=FAQ_Q1_BUTTON_TEXT, callback_data=FAQ_Q1_CALLBACK)
    )
    builder.row(
        InlineKeyboardButton(text=FAQ_Q2_BUTTON_TEXT, callback_data=FAQ_Q2_CALLBACK)
    )
    builder.row(
        InlineKeyboardButton(text=FAQ_Q3_BUTTON_TEXT, callback_data=FAQ_Q3_CALLBACK)
    )
    builder.row(
        InlineKeyboardButton(text=FAQ_Q4_BUTTON_TEXT, callback_data=FAQ_Q4_CALLBACK)
    )
    builder.row(
        InlineKeyboardButton(text=FAQ_Q5_BUTTON_TEXT, callback_data=FAQ_Q5_CALLBACK)
    )
    builder.row(
        InlineKeyboardButton(text=FAQ_Q6_BUTTON_TEXT, callback_data=FAQ_Q6_CALLBACK)
    )
    builder.row(
        InlineKeyboardButton(text=FAQ_Q7_BUTTON_TEXT, callback_data=FAQ_Q7_CALLBACK)
    )
    builder.row(
       InlineKeyboardButton(text=FAQ_Q8_BUTTON_TEXT, callback_data=FAQ_Q8_CALLBACK)
    )
    # Кнопка для возврата в главное меню (имитирует /start)
    # Убрал кнопку "Назад", так как это может конфликтовать с уже существующей кнопкой "Назад" из reply-клавиатуры.
    # Пользователь может использовать ее. Либо мы можем добавить кнопку "Закрыть FAQ"
    # которая просто удалит сообщение.
    # Оставим пока без кнопки "Назад" в этой инлайн-клавиатуре.
    # Пользователь нажмет "Частые вопросы" снова, если захочет.
    # Или стандартную кнопку "Назад" из ReplyKeyboard.

    return builder.as_markup() 