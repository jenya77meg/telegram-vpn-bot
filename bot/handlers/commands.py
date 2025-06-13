from aiogram import Router, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from datetime import datetime
from aiogram.filters import CommandObject
# Удаляем импорт I18n
# from aiogram.utils.i18n import I18n

from keyboards import get_main_menu_keyboard, get_welcome_keyboard, get_back_keyboard
# utils, marzban_api, get_marzban_profile_db, glv не используются в этой версии start, но могут быть нужны для других функций
from utils import goods, marzban_api # goods и marzban_api
from db.methods import (
    get_marzban_profile_db, 
    update_test_subscription_state,
    add_seller,
    remove_seller,
    get_seller_by_referral_code,
    get_all_sellers,
    add_referral,
    get_referral_by_user,
    create_payout,
    get_payouts_for_seller,
    get_seller_by_id,
    get_seller_by_tg_id,
    count_referrals_for_seller,
    update_seller_details,
    get_all_vpn_users_tg_id
)
import glv # glv
import asyncio
from aiogram.exceptions import TelegramBadRequest
import logging
from utils.marzban_api import panel
import html

router = Router(name="commands-router")

WELCOME_TEXT_RU = (
    "Добро пожаловать! Наш сервис предлогает:\n\n"  # Здесь одинарные \n, это корректно
    #  "Наш сервис предлагает доступ к chatgpt, gemini, claude и другим сервисам:\n"
    "✅ Простое подключение в пару кликов.\n"
    "✅ 7 дней бесплатного теста!\n"
    "✅ Высокую скорость и стабильное соединение.\n"
    "✅ Блокировка рекламы и трекеров.\n\n"
    "👇 Начните сейчас, выбрав одну из опций ниже:"
)

MAIN_MENU_TEXT_RU = "Главное меню"
TEXT_SUPPORT_LINK_MESSAGE = "Перейдите по <a href=\"{link}\">ссылке</a> и задайте нам вопрос. Мы всегда рады помочь 🤗"

@router.message(
    Command("help")
)
async def help_command(message: Message):
    await message.delete()
    await message.answer(
        TEXT_SUPPORT_LINK_MESSAGE.format(link=glv.config['SUPPORT_LINK']),
        reply_markup=get_back_keyboard()
    )

@router.message(
    Command("start")
)
async def start(message: Message, command: CommandObject):
    # --- Referral Logic ---
    referral_code_arg = command.args
    if referral_code_arg and referral_code_arg.startswith("ref_"):
        ref_code = referral_code_arg.split("_", 1)[1]
        user_id = message.from_user.id
        user_mention = f"@{message.from_user.username}" if message.from_user.username else f"ID: {user_id}"
        
        already_referred = await get_referral_by_user(user_id)

        if already_referred:
            # User is already a referral. Notify admin about the attempt to switch.
            original_seller = await get_seller_by_id(already_referred.seller_id)
            new_seller = await get_seller_by_referral_code(ref_code)

            # Check if it's a different seller and both exist, to avoid spamming on same-link clicks
            if new_seller and original_seller and new_seller.id != original_seller.id:
                admin_id = glv.config.get('ADMIN_ID')
                if admin_id:
                    text = (
                        f"🔔 Пользователь {user_mention}, который уже является рефералом продавца "
                        f"'{original_seller.name}' (код: {original_seller.referral_code}),\n"
                        f"попытался перейти по реферальной ссылке нового продавца "
                        f"'{new_seller.name}' (код: {new_seller.referral_code}).\n\n"
                        f"Никаких изменений не произведено."
                    )
                    await glv.bot.send_message(admin_id, text)
        else:
            # This is a new, unassigned user. Assign them.
            seller = await get_seller_by_referral_code(ref_code)
            if seller:
                await add_referral(user_id, seller.id)
                await glv.bot.send_message(
                    seller.tg_id,
                    f"🎉 У вас новый реферал! Пользователь {user_mention} присоединился по вашей ссылке."
                )

    await message.answer(WELCOME_TEXT_RU, reply_markup=get_welcome_keyboard())
    await message.answer(MAIN_MENU_TEXT_RU, reply_markup=get_main_menu_keyboard())

# Новая команда для имитации оплаты
@router.message(
    Command("simulate_payment_3months")
)
async def simulate_payment_3months(message: Message):
    admin_id_str = glv.config.get('ADMIN_ID')
    if admin_id_str:
        try:
            admin_id = int(admin_id_str)
            if message.from_user.id != admin_id:
                await message.answer("Эта команда доступна только администратору.")
                return
        except ValueError:
            await message.answer("ADMIN_ID в конфигурации некорректен. Команда не будет выполнена.")
            return
    else:
        # Если ADMIN_ID не указан, можно вывести предупреждение или разрешить для всех (для теста)
        print("[WARNING] ADMIN_ID не указан в конфигурации. Команда simulate_payment_3months доступна всем.")

    user_id = message.from_user.id
    chat_id = message.chat.id
    good_id = "vpn_3_months" # ID товара для 3 месяцев

    await message.answer(f"Имитация успешной оплаты для товара: {good_id}...")

    try:
        # Получаем информацию о товаре (количество месяцев)
        selected_good = goods.get(good_id)
        if not selected_good:
            await message.answer(f"Ошибка: Товар с ID {good_id} не найден в goods.json.")
            return
        
        # months = selected_good.get('months') # months будет использоваться только для сообщения
        # if not months:
        #     await message.answer(f"Ошибка: Для товара {good_id} не указано количество месяцев.")
        #     return

        # Вызов функции, которая обычно вызывается после успешной оплаты
        # Это marzban_api.generate_marzban_subscription
        new_marzban_user_data = await marzban_api.generate_marzban_subscription(
            str(user_id),       # tg_id пользователя
            selected_good       # Передаем весь объект товара
        )

        # Сброс флага тестовой подписки, если он был
        await update_test_subscription_state(user_id, is_test=False)

        # Для сообщения об успехе все еще можно использовать months из selected_good
        months_for_message = selected_good.get('months', 'не указано')
        expire_date_str = (datetime.fromtimestamp(new_marzban_user_data.get('expire')).strftime('%d.%m.%Y %H:%M') 
                           if new_marzban_user_data.get('expire') 
                           else 'нет данных')

        success_message = (
            f"✅ Успешная имитация оплаты!\n"
            f"Подписка на {months_for_message} мес. активирована.\n"
            f"Детали подписки (из Marzban):\n"
            f"Имя пользователя: {new_marzban_user_data.get('username')}\n"
            f"Статус: {new_marzban_user_data.get('status')}\n"
            f"Истекает: {expire_date_str}\n"
            f"URL подписки: {new_marzban_user_data.get('subscription_url')}"
        )
        await message.answer(success_message)

    except Exception as e:
        await message.answer(f"Произошла ошибка при имитации оплаты: {str(e)}")
        import traceback
        print(f"Error in simulate_payment_3months for user {user_id}: {str(e)}")
        print(traceback.format_exc())

# --- Seller Self-Service Commands ---

@router.message(Command("my_stats"))
async def my_stats_command(message: Message):
    seller = await get_seller_by_tg_id(message.from_user.id)
    if not seller:
        await message.answer("Эта команда доступна только для зарегистрированных партнеров.")
        return
        
    referral_count = await count_referrals_for_seller(seller.id)
    
    # Escape user data to prevent HTML injection
    safe_seller_name = html.escape(seller.name)
    safe_referral_code = html.escape(seller.referral_code)

    response = (
        f"📊 Ваш личный кабинет, {safe_seller_name}:\n\n"
        f"️Ваш реферальный код: <code>{safe_referral_code}</code>\n"
        f"💰 Текущий баланс: <b>{seller.balance / 100}</b> руб.\n"
        f"👥 Привлечено пользователей: <b>{referral_count}</b>\n\n"
        f"Используйте команду /my_link, чтобы получить вашу персональную ссылку."
    )
    await message.answer(response, parse_mode="HTML")

@router.message(Command("my_link"))
async def my_link_command(message: Message):
    seller = await get_seller_by_tg_id(message.from_user.id)
    if not seller:
        await message.answer("Эта команда доступна только для зарегистрированных партнеров.")
        return

    bot_user = await glv.bot.get_me()
    bot_username = bot_user.username
    link = f"https://t.me/{bot_username}?start=ref_{seller.referral_code}"
    
    response = (
        f"🔗 Ваша персональная реферальная ссылка:\n\n"
        f"<code>{link}</code>\n\n"
        f"Поделитесь этой ссылкой с вашими клиентами для автоматического отслеживания."
    )
    await message.answer(response, parse_mode="HTML")

# --- Admin Commands for Seller Management ---
async def is_admin(message: Message) -> bool:
    admin_id_str = glv.config.get('ADMIN_ID')
    if not admin_id_str or not admin_id_str.isdigit():
        return False
    return message.from_user.id == int(admin_id_str)

@router.message(Command("add_seller"))
async def add_seller_command(message: Message, command: CommandObject):
    if not await is_admin(message):
        await message.answer("Эта команда доступна только администратору.")
        return

    args = command.args
    if not args or len(args.split()) != 3:
        await message.answer("Использование: /add_seller &lt;Имя&gt; &lt;Telegram_ID&gt; &lt;Реферальный_код&gt;")
        return
    
    name, tg_id_str, referral_code = args.split()

    if not tg_id_str.isdigit():
        await message.answer("Telegram ID должен быть числом.")
        return

    tg_id = int(tg_id_str)

    try:
        await add_seller(name, tg_id, referral_code)
        await message.answer(f"✅ Продавец '{name}' с кодом '{referral_code}' успешно добавлен.")
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при добавлении продавца: {e}")

@router.message(Command("remove_seller"))
async def remove_seller_command(message: Message, command: CommandObject):
    if not await is_admin(message):
        await message.answer("Эта команда доступна только администратору.")
        return

    referral_code = command.args
    if not referral_code:
        await message.answer("Использование: /remove_seller &lt;Реферальный_код&gt;")
        return

    try:
        await remove_seller(referral_code.strip())
        await message.answer(f"✅ Продавец с кодом '{referral_code}' успешно удален.")
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при удалении продавца: {e}")

@router.message(Command("list_sellers"))
async def list_sellers_command(message: Message):
    if not await is_admin(message):
        await message.answer("Эта команда доступна только администратору.")
        return

    sellers = await get_all_sellers()
    if not sellers:
        await message.answer("Список продавцов пуст.")
        return

    response = "👥 Список продавцов:\n\n"
    for seller in sellers:
        response += f"Имя: {seller.name}\n"
        response += f"Telegram ID: {seller.tg_id}\n"
        response += f"Реферальный код: {seller.referral_code}\n"
        response += f"Баланс: {seller.balance / 100} руб.\n" # Assuming balance is in kopecks/cents
        response += "-----\n"
    
    await message.answer(response)

@router.message(Command("payout"))
async def payout_command(message: Message, command: CommandObject):
    if not await is_admin(message):
        await message.answer("Эта команда доступна только администратору.")
        return

    args = command.args
    if not args or len(args.split()) < 2:
        await message.answer("Использование: /payout &lt;Реферальный_код&gt; &lt;Сумма_в_рублях&gt; [Комментарий]")
        return
    
    parts = args.split()
    referral_code = parts[0]
    amount_str = parts[1]
    comment = " ".join(parts[2:]) if len(parts) > 2 else None

    if not amount_str.replace('.', '', 1).isdigit():
        await message.answer("Сумма должна быть числом.")
        return
    
    amount_rub = float(amount_str)
    amount_kopecks = int(amount_rub * 100)

    seller = await get_seller_by_referral_code(referral_code)
    if not seller:
        await message.answer(f"Продавец с кодом '{referral_code}' не найден.")
        return

    success = await create_payout(seller.id, amount_kopecks, comment)

    if success:
        await message.answer(
            f"✅ Выплата в размере {amount_rub} руб. для продавца '{seller.name}' успешно зарегистрирована.\n"
            f"Новый баланс: {(seller.balance - amount_kopecks) / 100} руб."
        )
        # Notify seller
        await glv.bot.send_message(
            seller.tg_id,
            f"💸 Вам была произведена выплата в размере {amount_rub} руб.\n"
            f"Комментарий: {comment or 'Без комментария'}\n"
            f"Спасибо за вашу работу!"
        )
    else:
        await message.answer(
            f"❌ Не удалось произвести выплату. "
            f"Возможно, баланс продавца ({seller.balance / 100} руб.) меньше суммы выплаты."
        )

@router.message(Command("payout_history"))
async def payout_history_command(message: Message, command: CommandObject):
    if not await is_admin(message):
        await message.answer("Эта команда доступна только администратору.")
        return

    referral_code = command.args
    if not referral_code:
        await message.answer("Использование: /payout_history &lt;Реферальный_код&gt;")
        return

    seller = await get_seller_by_referral_code(referral_code.strip())
    if not seller:
        await message.answer(f"Продавец с кодом '{referral_code}' не найден.")
        return
        
    payouts = await get_payouts_for_seller(seller.id)

    if not payouts:
        await message.answer(f"История выплат для продавца '{seller.name}' пуста.")
        return

    response = f"🧾 История выплат для '{seller.name}':\n\n"
    for payout in payouts:
        # Parse ISO string to datetime object, then format it
        payout_date = datetime.fromisoformat(payout.payout_date).strftime('%d.%m.%Y %H:%M')
        response += f"Дата: {payout_date}\n"
        response += f"Сумма: {payout.amount / 100} руб.\n"
        response += f"Комментарий: {payout.comment or 'Нет'}\n"
        response += "-----\n"
        
    await message.answer(response)

@router.message(Command("edit_seller"))
async def edit_seller_command(message: Message, command: CommandObject):
    if not await is_admin(message):
        await message.answer("Эта команда доступна только администратору.")
        return

    args = command.args
    if not args or len(args.split()) != 3:
        await message.answer("Использование: /edit_seller &lt;старый_код&gt; &lt;поле&gt; &lt;новое_значение&gt;\nПоля: `name`, `tg_id`, `code`")
        return
        
    current_code, field, new_value = args.split()

    if field not in ['name', 'tg_id', 'code']:
        await message.answer(f"Неизвестное поле '{field}'. Доступные поля: `name`, `tg_id`, `code`.")
        return

    if field == 'tg_id' and not new_value.isdigit():
        await message.answer("Новый Telegram ID должен быть числом.")
        return

    # To avoid confusion, let's rename 'code' to 'referral_code' for the DB method
    db_field = 'referral_code' if field == 'code' else field
    
    success = await update_seller_details(current_code, db_field, new_value)

    if success:
        await message.answer(f"✅ Данные продавца с (бывшим) кодом '{current_code}' успешно обновлены.")
    else:
        await message.answer(f"❌ Не удалось обновить данные. Возможно, новый реферальный код '{new_value}' уже занят.")

@router.message(Command("give_sub"))
async def give_sub_command(message: Message, command: CommandObject):
    if not await is_admin(message):
        return

    args = command.args
    if not args or len(args.split()) != 2:
        await message.answer(
            "Использование: /give_sub &lt;Telegram_ID&gt; &lt;ID_Товара&gt;\n"
            "Пример: `/give_sub 123456789 vpn_1_month`"
        )
        return

    tg_id_str, good_id = args.split()

    if not tg_id_str.isdigit():
        await message.answer("Telegram ID должен быть числом.")
        return

    user_tg_id = int(tg_id_str)
    selected_good = goods.get(good_id)

    if not selected_good:
        await message.answer(f"Товар с ID `{good_id}` не найден в `goods.json`.")
        return

    try:
        # 1. Issue the subscription
        await marzban_api.generate_marzban_subscription(str(user_tg_id), selected_good)
        await update_test_subscription_state(user_tg_id, is_test=False)
        await message.answer(f"✅ Подписка '{selected_good['title']}' успешно выдана пользователю {user_tg_id}.")

        # 2. Notify the user
        await glv.bot.send_message(
            user_tg_id,
            f"🎉 Поздравляем! Администратор выдал вам подписку \"{selected_good['title']}\".\n"
            "Она уже активна и доступна в разделе \"Мой профиль 👤\"."
        )
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при выдаче подписки: {e}")

@router.message(Command("broadcast"))
async def broadcast_command(message: Message, command: CommandObject):
    if not await is_admin(message):
        return # Silently ignore for non-admins

    if not command.args:
        await message.answer(
            "Пожалуйста, укажите сообщение для рассылки.\n"
            "Пример: `/broadcast Сервер будет перезагружен в 15:00`"
        )
        return

    text = command.args
    users = await get_all_vpn_users_tg_id()
    
    await message.answer(f"📢 Начинаю рассылку для {len(users)} пользователей...")
    
    success_count = 0
    fail_count = 0
    
    for user_id in users:
        try:
            await glv.bot.send_message(user_id, text, parse_mode="HTML")
            success_count += 1
        except TelegramBadRequest as e:
            # Handle cases where user blocked the bot, etc.
            logging.warning(f"Failed to send message to {user_id}: {e}")
            fail_count += 1
        except Exception as e:
            logging.error(f"An unexpected error occurred when sending to {user_id}: {e}")
            fail_count += 1
        await asyncio.sleep(0.1) # Rate limit sleeping

    await message.answer(
        f"✅ Рассылка завершена!\n\n"
        f"Успешно отправлено: {success_count}\n"
        f"Не удалось отправить: {fail_count}"
    )

@router.message(Command("broadcast_active"))
async def broadcast_active_command(message: Message, command: CommandObject):
    if not await is_admin(message):
        return

    if not command.args:
        await message.answer(
            "Пожалуйста, укажите сообщение для рассылки.\n"
            "Пример: `/broadcast_active Сервер будет перезагружен в 15:00`"
        )
        return

    text = command.args
    
    try:
        marzban_users = await panel.get_users()
        # Filter for active users where username is a valid TG ID
        active_users_ids = [
            int(user['username']) 
            for user in marzban_users.get('users', []) 
            if user['status'] == 'active' and user['username'].isdigit()
        ]
    except Exception as e:
        await message.answer(f"❌ Не удалось получить список активных пользователей из Marzban: {e}")
        return

    await message.answer(f"📢 Начинаю рассылку для {len(active_users_ids)} активных подписчиков...")
    
    success_count = 0
    fail_count = 0
    
    for user_id in active_users_ids:
        try:
            await glv.bot.send_message(user_id, text, parse_mode="HTML")
            success_count += 1
        except TelegramBadRequest as e:
            logging.warning(f"Failed to send message to {user_id}: {e}")
            fail_count += 1
        except Exception as e:
            logging.error(f"An unexpected error occurred when sending to {user_id}: {e}")
            fail_count += 1
        await asyncio.sleep(0.1)

    await message.answer(
        f"✅ Рассылка для активных подписчиков завершена!\n\n"
        f"Успешно отправлено: {success_count}\n"
        f"Не удалось отправить: {fail_count}"
    )

def register_commands(dp: Dispatcher):
    dp.include_router(router)
