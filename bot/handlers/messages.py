from aiogram import Router, F
from aiogram import Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import re # Оставим re, если escape_markdown_v2 используется где-то еще или планируется

from .commands import start
# Убедись, что get_faq_questions_keyboard импортируется
from keyboards import (
    get_buy_menu_keyboard, get_back_keyboard, get_main_menu_keyboard,
    get_profile_actions_keyboard, get_faq_questions_keyboard # <--- ВОТ ОН
)
from db.methods import can_get_test_sub, update_test_subscription_state, get_marzban_profile_db, get_user_email
from utils import marzban_api
import glv

router = Router(name="messages-router")

TEXT_BUY_SUB = "Купить подписку 🛒"
TEXT_MY_PROFILE = "Мой профиль 👤"
TEXT_FAQ = "Частые вопросы ℹ️" # Эта константа уже есть
TEXT_SUPPORT = "Поддержка ❤️"
TEXT_BACK = "⏪ Назад"

TEXT_CHOOSE_TARIFF = "Выберите подходящий тариф ⬇️"
TEXT_PROFILE_NOT_ACTIVE = "Ваш профиль сейчас не активен. Воспользуйтесь меню или командой /start."
TEXT_SUBSCRIPTION_PAGE = "Страница подписки ⬇️"
TEXT_FOLLOW_LINK = "Перейдите по <a href=\"{link}\">ссылке</a> 🔗" # Эта тоже есть
TEXT_SUPPORT_LINK_MESSAGE = "Перейдите по <a href=\"{link}\">ссылке</a> и задайте нам вопрос. Мы всегда рады помочь 🤗" # И эта

# Новая константа для вступления в FAQ
TEXT_FAQ_INTRO = "Выберите интересующий вас вопрос:"

# New constants for the profile section
TEXT_SUBSCRIPTION_INSTRUCTION = "Подписка и инструкция доступны по ссылке ниже"
BUTTON_TEXT_GO_TO_SITE = "Перейти на сайт"

# Текст для кнопки "Назад"
TEXT_MAIN_MENU_FOR_BACK_BUTTON = "Главное меню"

# Вспомогательная функция для экранирования MarkdownV2 (оставим на случай, если понадобится)
def escape_markdown_v2(text: str) -> str:
    """Экранирует специальные символы для MarkdownV2."""
    if not isinstance(text, str):
        text = str(text)
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

@router.message(F.text == TEXT_BUY_SUB)
async def buy(message: Message):
    await message.delete()
    await message.answer(TEXT_CHOOSE_TARIFF, reply_markup=get_buy_menu_keyboard())

@router.message(F.text == TEXT_MY_PROFILE)
async def profile(message: Message):
    await message.delete()
    tg_id = message.from_user.id
    user_full_name = message.from_user.full_name
    
    profile_info_parts = [f"Ваш профиль:<b>{user_full_name}</b>"]
    profile_info_parts.append(f"Telegram ID:<b>{tg_id}</b>")

    # Получаем email пользователя
    user_email = await get_user_email(tg_id)
    if user_email:
        profile_info_parts.append(f"Ваш email: <b>{user_email}</b>")
    else:
        profile_info_parts.append("Ваш email: <b>Не указан</b>")

    # ... (остальная логика функции profile из твоего файла) ...
    marzban_user_data = await marzban_api.get_marzban_profile(tg_id) # Добавил для полноты, если этого нет
    db_user_profile = await get_marzban_profile_db(tg_id) # Добавил для полноты

    status_sub_val = "Не определен"
    type_sub_val = "Отсутствует"
    expire_date_val = "Нет данных"
    
    show_renew_button = False
    show_buy_button = False

    if marzban_user_data:
        marzban_status = marzban_user_data.get('status', 'disabled')
        if marzban_status == 'active':
            status_sub_val = "Активна ✅"
        elif marzban_status == 'disabled':
            status_sub_val = "Отключена 🔘"
        elif marzban_status == 'expired':
            status_sub_val = "Истекла ⌛️"
        elif marzban_status == 'limited':
            status_sub_val = "Ограничена ⚠️"
        else:
            status_sub_val = f"Неизвестный статус ({marzban_status}) ❓"

        expire_timestamp = marzban_user_data.get('expire')
        if expire_timestamp:
            expire_datetime = datetime.fromtimestamp(expire_timestamp)
            expire_date_val = expire_datetime.strftime("%d.%m.%Y %H:%M")
            if marzban_status == 'active' and (expire_datetime - datetime.now()) < timedelta(days=5):
                show_renew_button = True
        else:
            expire_date_val = "Безлимитная (или нет данных)"
            if marzban_status != 'active':
                 show_buy_button = True 

        if db_user_profile and db_user_profile.test:
            if marzban_status == 'active' or (marzban_status == 'expired' and expire_timestamp and datetime.fromtimestamp(expire_timestamp) > datetime.now() - timedelta(days=1)):
                type_sub_val = "Пробная 🚀"
                show_buy_button = True 
            elif marzban_status == 'disabled' and not expire_timestamp :
                 type_sub_val = "Пробная (отменена) 🚫"
                 show_buy_button = True
            else: 
                type_sub_val = "Пробная (завершена) 🏁"
                show_buy_button = True 
        elif marzban_status == 'active': 
            type_sub_val = "Платная 💳"
        else: 
            type_sub_val = "Платная (неактивна) 💤"
            show_buy_button = True
    else: 
        status_sub_val = "Отсутствует в VPN системе 🤷‍♂️"
        type_sub_val = "Отсутствует"
        expire_date_val = "-"
        show_buy_button = True 
        if db_user_profile and db_user_profile.test: 
             type_sub_val = "Пробная (не найдена в VPN) 🤔"
             
    profile_info_parts.append(f"Статус подписки: <b>{status_sub_val}</b>")
    profile_info_parts.append(f"Тип подписки: <b>{type_sub_val}</b>")
    profile_info_parts.append(f"Дата окончания: <b>{expire_date_val}</b>")

    reply_markup_profile: InlineKeyboardMarkup | None = get_profile_actions_keyboard(show_renew=show_renew_button, show_buy=show_buy_button) # Переименовал переменную, чтобы не было конфликта
    
    await message.answer("\n".join(profile_info_parts), reply_markup=reply_markup_profile, parse_mode="HTML")

    if marzban_user_data and marzban_user_data.get('subscription_url'):
        site_button = InlineKeyboardButton(
            text=BUTTON_TEXT_GO_TO_SITE,
            url=marzban_user_data.get('subscription_url')
        )
        site_keyboard = InlineKeyboardMarkup(inline_keyboard=[[site_button]])
        await message.answer(
            TEXT_SUBSCRIPTION_INSTRUCTION,
            reply_markup=site_keyboard,
            disable_notification=True
        )

@router.message(F.text == TEXT_FAQ)
async def information(message: Message): # Это измененный обработчик
    await message.delete()
    await message.answer(
        TEXT_FAQ_INTRO,
        reply_markup=get_faq_questions_keyboard() # Используем новую клавиатуру
    )

@router.message(F.text == TEXT_SUPPORT)
async def support(message: Message):
    await message.delete()
    await message.answer(
        TEXT_SUPPORT_LINK_MESSAGE.format(link=glv.config['SUPPORT_LINK']),
        reply_markup=get_back_keyboard()) # Здесь get_back_keyboard() - это кнопка "Назад" ведущая в FAQ или в главное меню?

@router.message(F.text == TEXT_BACK)
async def back_to_main_menu(message: Message):
    await message.delete()
    await message.answer(TEXT_MAIN_MENU_FOR_BACK_BUTTON, reply_markup=get_main_menu_keyboard())

def register_messages(dp: Dispatcher):
    dp.include_router(router)
