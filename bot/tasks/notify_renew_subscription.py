import asyncio
import logging
import time
from datetime import datetime, timedelta

from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.methods import get_marzban_profile_db
from utils.marzban_api import panel

import glv


def format_relative_date(expire_timestamp: int) -> str:
    """Форматирует дату в человекочитаемый относительный формат."""
    now = datetime.now()
    expire_dt = datetime.fromtimestamp(expire_timestamp)
    time_str = expire_dt.strftime('%H:%M')

    if now.date() == expire_dt.date():
        return f"сегодня в {time_str}"
    
    if (expire_dt.date() - now.date()) == timedelta(days=1):
        return f"завтра в {time_str}"
    
    # Для остальных случаев - более приятный формат
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    month_name = months[expire_dt.month - 1]
    return f"{expire_dt.day} {month_name} в {time_str}"


async def notify_users_to_renew_sub():
    try:
        users_to_notify = await get_marzban_users_to_notify()
        if not users_to_notify:
            return

        for user_data in users_to_notify:
            username = user_data.get('username')
            if not username or not username.isdigit():
                continue
            
            tg_id = int(username)
            user = await get_marzban_profile_db(tg_id)

            if user is None:
                logging.warning(f"User with tg_id {tg_id} from Marzban not found in local DB.")
                continue

            try:
                # Форматируем дату окончания с помощью новой функции
                expire_timestamp = user_data.get('expire')
                expire_date_str = format_relative_date(expire_timestamp)
                
                chat_member = await glv.bot.get_chat_member(user.tg_id, user.tg_id)
                message = (
                    f"Здравствуйте, {chat_member.user.first_name} 👋🏻\n\n"
                    "Спасибо, что пользуетесь нашим сервисом ❤️\n️\n"
                    f"Срок действия вашей подписки истекает <b>{expire_date_str}</b>.\n\n"
                    "Чтобы продлить ее, нажмите на кнопку ниже 👇"
                )

                # Создаем инлайн-кнопку
                builder = InlineKeyboardBuilder()
                builder.button(text="Продлить подписку 🛒", callback_data="buy_subscription_action")
                
                await glv.bot.send_message(
                    user.tg_id, 
                    message, 
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Failed to send renewal notification to user {user.tg_id}: {e}")

    except Exception as e:
        logging.error(f"An error occurred in the notify_users_to_renew_sub task: {e}")


async def get_marzban_users_to_notify():
    try:
        res = await panel.get_users()
        if res is None or 'users' not in res:
            return None
        users = res.get('users', [])
        return filter(filter_users_to_notify, users)
    except Exception as e:
        logging.error(f"Failed to get users from Marzban for notification task: {e}")
        return None


def filter_users_to_notify(user):
    user_expire_date = user.get('expire')
    if not isinstance(user_expire_date, int):
        return False
    # Уведомляем тех, чья подписка истекает в ближайшие 24-48 часов
    # (Это более стандартный и менее агрессивный подход, чем 12-36 часов)
    now = int(time.time())
    from_date = now + (24 * 60 * 60) # 24 часа от сейчас
    to_date = now + (48 * 60 * 60)   # 48 часов от сейчас
    return from_date < user_expire_date < to_date
