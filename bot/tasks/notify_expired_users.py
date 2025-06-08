import asyncio
import logging
import time
from datetime import datetime

from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.methods import get_marzban_profile_db
from utils.marzban_api import panel
import glv


def filter_expired_users(user):
    """Фильтрует пользователей, чья подписка истекла за последние 24 часа."""
    user_expire_date = user.get('expire')
    status = user.get('status')

    # Нам интересны только пользователи со статусом 'expired' или 'disabled'
    if not isinstance(user_expire_date, int) or status not in ['expired', 'disabled']:
        return False

    now = int(time.time())
    # Проверяем, что срок истек в промежутке от 24 часов назад до текущего момента.
    # Это гарантирует, что мы отправим уведомление только один раз.
    twenty_four_hours_ago = now - (24 * 60 * 60)
    return twenty_four_hours_ago < user_expire_date <= now


async def get_marzban_users_to_notify_expired():
    """Получает из Marzban список пользователей для уведомления об истечении подписки."""
    try:
        res = await panel.get_users()
        if not res or 'users' not in res:
            return None
        users = res.get('users', [])
        return filter(filter_expired_users, users)
    except Exception as e:
        logging.error(f"Failed to get users from Marzban for expired notification task: {e}")
        return None


async def notify_expired_users_task():
    """Задача по отправке уведомлений пользователям с истекшей подпиской."""
    try:
        users_to_notify = await get_marzban_users_to_notify_expired()
        if not users_to_notify:
            return

        for user_data in users_to_notify:
            username = user_data.get('username')
            if not username or not username.isdigit():
                continue
            
            tg_id = int(username)
            user = await get_marzban_profile_db(tg_id)

            if user is None:
                logging.warning(f"Expired user with tg_id {tg_id} from Marzban not found in local DB.")
                continue

            try:
                chat_member = await glv.bot.get_chat_member(user.tg_id, user.tg_id)
                message = (
                    f"Здравствуйте, {chat_member.user.first_name}.\n\n"
                    "Срок действия вашей подписки истек, и доступ к VPN был ограничен.\n\n"
                    "Чтобы возобновить доступ, пожалуйста, оплатите подписку."
                )

                builder = InlineKeyboardBuilder()
                builder.button(text="Оплатить подписку 🛒", callback_data="buy_subscription_action")
                
                await glv.bot.send_message(
                    user.tg_id, 
                    message, 
                    reply_markup=builder.as_markup()
                )
            except Exception as e:
                logging.error(f"Failed to send expired notification to user {user.tg_id}: {e}")

    except Exception as e:
        logging.error(f"An error occurred in the notify_expired_users_task: {e}") 