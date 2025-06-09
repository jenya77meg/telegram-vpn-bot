import uuid
import logging
import ipaddress
import time
import json

from aiohttp.web_request import Request
from aiohttp import web

from db.methods import (
    get_marzban_profile_db,
    get_yookassa_payment,
    get_cryptomus_payment,
    delete_payment,
    get_user_display_info,
    update_test_subscription_state,
    get_referral_by_user,
    get_seller_by_id,
    update_seller_balance
)
from keyboards import get_main_menu_keyboard
from utils import webhook_data, goods, marzban_api
import glv

YOOKASSA_IPS = (
    "185.71.76.0/27",
    "185.71.77.0/27",
    "77.75.153.0/25",
    "77.75.156.11",
    "77.75.156.35",
    "77.75.154.128/25",
    "2a02:5180::/32"
)

async def handle_referral_commission(user_tg_id: int, good: dict):
    """
    Handles calculating and distributing referral commission after a successful payment.
    """
    try:
        referral = await get_referral_by_user(user_tg_id)
        if not referral:
            return

        seller = await get_seller_by_id(referral.seller_id)
        if not seller:
            return

        payment_amount_rub = good.get("price", {}).get("ru", 0)
        if payment_amount_rub <= 0:
            return
            
        commission_rub = payment_amount_rub * 0.50
        commission_kopecks = int(commission_rub * 100)

        await update_seller_balance(seller.id, commission_kopecks)

        user_info = await get_marzban_profile_db(user_tg_id)
        user_mention = f"@{user_info.telegram_username}" if user_info.telegram_username else f"ID: {user_tg_id}"

        # Notification to admin
        admin_id = glv.config.get('ADMIN_ID')
        if admin_id:
            admin_text = (
                f"💰 Реферальное начисление!\n\n"
                f"Продавец: {seller.name}\n"
                f"Пользователь: {user_mention}\n"
                f"Сумма покупки: {payment_amount_rub} руб.\n"
                f"Комиссия (50%): {commission_rub} руб."
            )
            await glv.bot.send_message(admin_id, admin_text)

        # Notification to seller
        seller_text = (
            f"🎉 Ваш реферал {user_mention} совершил покупку!\n\n"
            f"Сумма покупки: {payment_amount_rub} руб.\n"
            f"Ваша комиссия (50%): {commission_rub} руб.\n\n"
            f"Спасибо!"
        )
        await glv.bot.send_message(seller.tg_id, seller_text)

    except Exception as e:
        logging.error(f"Error in handle_referral_commission: {e}")


async def check_crypto_payment(request: Request):
    client_ip = request.headers.get('CF-Connecting-IP') or request.headers.get('X-Real-IP') or request.headers.get('X-Forwarded-For') or request.remote
    if client_ip not in ["91.227.144.54"]:
        return web.Response(status=403)
    data = await request.json()
    if not webhook_data.check(data, glv.config['CRYPTO_TOKEN']):
        return web.Response(status=403)
    payment = await get_cryptomus_payment(data['order_id'])
    if payment == None:
        return web.Response()
    if data['status'] in ['paid', 'paid_over']:
        good = goods.get(payment.callback)
        user = await get_marzban_profile_db(payment.tg_id)
        marzban_user_data = await marzban_api.generate_marzban_subscription(str(user.tg_id), good)
        await update_test_subscription_state(payment.tg_id, is_test=False)
        
        # Handle referral commission
        await handle_referral_commission(payment.tg_id, good)

        text = f"Спасибо за ваш выбор ❤️\n️\nВаша подписка оформлена и доступна в разделе \"Мой профиль 👤\"."
        await glv.bot.send_message(payment.chat_id,
            text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
        await delete_payment(payment.payment_uuid)
    if data['status'] == 'cancel':
        await delete_payment(payment.payment_uuid)
    return web.Response()

async def check_yookassa_payment(request: Request):
    client_ip = request.headers.get('CF-Connecting-IP') or request.headers.get('X-Real-IP') or request.headers.get('X-Forwarded-For') or request.remote
    f = True
    for subnet in YOOKASSA_IPS:
        if "/" in subnet:
            if ipaddress.ip_address(client_ip) in ipaddress.ip_network(subnet):
                f = False
                break
        else:
            if client_ip == subnet:
                f = False
                break
    if f:
        return web.Response(status=403)
    data = (await request.json())['object']
    payment = await get_yookassa_payment(data['id'])
    if payment == None:
        return web.Response()
    if data['status'] in ['succeeded']:
        good = goods.get(payment.callback)
        user = await get_marzban_profile_db(payment.tg_id)
        marzban_user_data = await marzban_api.generate_marzban_subscription(str(user.tg_id), good)
        await update_test_subscription_state(payment.tg_id, is_test=False)

        # Handle referral commission
        await handle_referral_commission(payment.tg_id, good)

        text = f"Спасибо за ваш выбор ❤️\n️\nВаша подписка оформлена и доступна в разделе \"Мой профиль 👤\"."
        await glv.bot.send_message(payment.chat_id,
            text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
        await delete_payment(payment.payment_id)
    if data['status'] == 'canceled':
        await delete_payment(payment.payment_id)
    return web.Response()

async def get_user_display_info_endpoint(request):
    """API endpoint для получения читаемой информации о пользователе"""
    vpn_id = request.match_info.get('vpn_id', '')
    if not vpn_id:
        return web.json_response({'error': 'vpn_id is required'}, status=400)
    
    user_info = await get_user_display_info(vpn_id)
    return web.json_response(user_info)
