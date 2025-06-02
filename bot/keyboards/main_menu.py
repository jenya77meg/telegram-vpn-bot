from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
# Удаляем импорт I18n
# from aiogram.utils.i18n import I18n
from aiogram.utils.keyboard import ReplyKeyboardBuilder
# import glv # glv не используется в этом файле сейчас

# Тексты кнопок на русском
BTN_BUY_SUB_RU = "Купить подписку 🛒"
BTN_MY_PROFILE_RU = "Мой профиль 👤"
BTN_FAQ_RU = "Частые вопросы ℹ️"
BTN_SUPPORT_RU = "Поддержка ❤️"

# Функция больше не принимает lang_code
def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    # Удаляем все, что связано с i18n
    # i18n = I18n.get_current(no_error=True)

    # buy_text_msgid = "..."
    # my_subscription_text_msgid = "..."
    # faq_text_msgid = "..."
    # support_text_msgid = "..."

    # translated_buy_text = buy_text_msgid
    # translated_my_subscription_text = my_subscription_text_msgid
    # translated_faq_text = faq_text_msgid
    # translated_support_text = support_text_msgid

    # if i18n:
    #     print(f"[DEEP_DEBUG_KEYBOARD_MAIN] ...")
    #     translated_buy_text = i18n.gettext(buy_text_msgid)
    #     # ... и так далее для других кнопок
    #     print(f"[DEEP_DEBUG_KEYBOARD_MAIN] ...")
    # else:
    #     print(f"[DEEP_DEBUG_KEYBOARD_MAIN] ...")

    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=BTN_BUY_SUB_RU),
        KeyboardButton(text=BTN_MY_PROFILE_RU)
    )
    builder.row(
        KeyboardButton(text=BTN_FAQ_RU),     # Используем русскую строку
        KeyboardButton(text=BTN_SUPPORT_RU) # Используем русскую строку
    )
    return builder.as_markup(resize_keyboard=True)   
