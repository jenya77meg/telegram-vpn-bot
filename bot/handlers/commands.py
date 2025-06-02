from aiogram import Router, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from datetime import datetime
# Удаляем импорт I18n
# from aiogram.utils.i18n import I18n

from keyboards import get_main_menu_keyboard, get_welcome_keyboard
# utils, marzban_api, get_marzban_profile_db, glv не используются в этой версии start, но могут быть нужны для других функций
from utils import goods, marzban_api # goods и marzban_api
from db.methods import get_marzban_profile_db, update_test_subscription_state # get_marzban_profile_db и update_test_subscription_state
import glv # glv

router = Router(name="commands-router")

WELCOME_TEXT_RU = (
    "Добро пожаловать в мир свободного и быстрого интернета!\n\n"  # Здесь одинарные \n, это корректно
    "Наш VPN предлагает:\n"
    "✅ 7 дней бесплатного теста — попробуйте без обязательств!\n"
    "✅ Высокую скорость и стабильное соединение для стриминга, игр и работы.\n"
    "✅ Безлимитный трафик — пользуйтесь сколько угодно.\n"
    "✅ Простое подключение в пару кликов.\n\n"
    "👇 Начните сейчас, выбрав одну из опций ниже:"
)

MAIN_MENU_TEXT_RU = "Главное меню"

@router.message(
    Command("start")
)
# Убираем i18n из аргументов
async def start(message: Message):
    # Убираем всю логику, связанную с i18n и lang_code
    # user_lang_code = message.from_user.language_code
    # print(f"[DEEP_DEBUG] User language_code: {user_lang_code}")
    
    # effective_lang_code = 'ru' 

    # print(f"[DEEP_DEBUG] Using effective_lang_code: {effective_lang_code} for aiogram's i18n.gettext().")

    # welcome_text_msgid = "..."
    # main_menu_msgid = "..."

    # translated_welcome_text = welcome_text_msgid
    # translated_main_menu_text = main_menu_msgid

    # if i18n:
    #     translated_welcome_text = i18n.gettext(welcome_text_msgid)
    #     translated_main_menu_text = i18n.gettext(main_menu_msgid)  
    
    # print(f"[DEEP_DEBUG] Welcome text msgid: '{welcome_text_msgid}'")
    # print(f"[DEEP_DEBUG] Translated welcome text by i18n.gettext(): '{translated_welcome_text}'")
    # print(f"[DEEP_DEBUG] Main menu msgid: '{main_menu_msgid}'")
    # print(f"[DEEP_DEBUG] Translated main menu text by i18n.gettext(): '{translated_main_menu_text}'")

    # Клавиатуры теперь не принимают lang_code
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
        months_for_message = selected_good.get('months', 'N/A')

        success_message = (
            f"✅ Успешная имитация оплаты!\n"
            f"Подписка на {months_for_message} мес. активирована.\n"
            f"Детали подписки (из Marzban):"
            f"Username: {new_marzban_user_data.get('username')}\n"
            f"Status: {new_marzban_user_data.get('status')}\n"
            f"Expires: {datetime.fromtimestamp(new_marzban_user_data.get('expire')).strftime('%d.%m.%Y %H:%M') if new_marzban_user_data.get('expire') else 'N/A'}\n"
            f"Subscription URL: {new_marzban_user_data.get('subscription_url')}"
        )
        await message.answer(success_message)

    except Exception as e:
        await message.answer(f"Произошла ошибка при имитации оплаты: {str(e)}")
        import traceback
        print(f"Error in simulate_payment_3months for user {user_id}: {str(e)}")
        print(traceback.format_exc())

def register_commands(dp: Dispatcher):
    dp.include_router(router)
