import asyncio
import time

from db.methods import get_marzban_profile_by_vpn_id

import glv

async def notify_users_to_renew_sub():
    marzban_users_to_notify = await get_marzban_users_to_notify()
    if marzban_users_to_notify is None:
        return None
    for vpn_id in list_vpn_id:
        user = await get_marzban_profile_by_vpn_id(vpn_id)
        if user is None:
            continue
        chat_member = await glv.bot.get_chat_member(user.tg_id, user.tg_id)
        if chat_member is None:
            continue
        message = f"Здравствуйте, {chat_member.user.first_name} 👋🏻\n\nСпасибо, что пользуетесь нашим сервисом ❤️\n️\nВаша подписка на VPN истекает завтра в конце дня.\n️\nЧтобы продлить ее, просто перейдите в раздел \"Купить подписку🛒\" и произведите оплату."
        await glv.bot.send_message(user.tg_id, message)

async def get_marzban_users_to_notify():
    res = await marzban_api.panel.get_users()
    if res is None:
        return None
    users = res['users']
    return filter(filter_users_to_notify, users)

def filter_users_to_notify(user):
    user_expire_date = user['expire']
    if user_expire_date is None:
        return False
    from_date = int(time.time()) + 60 * 60 * 12
    to_date = from_date + 60 * 60 * 24
    return from_date < user_expire_date < to_date
