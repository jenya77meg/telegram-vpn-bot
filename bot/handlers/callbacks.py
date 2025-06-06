from datetime import datetime, timedelta

from aiogram import Router, F, types
from aiogram import Dispatcher
from aiogram.types import CallbackQuery, Message

from keyboards import get_payment_keyboard, get_pay_keyboard, get_buy_menu_keyboard
from utils import goods, yookassa, cryptomus, marzban_api
from db.methods import can_get_test_sub, update_test_subscription_state, get_marzban_profile_db
import glv

router = Router(name="callbacks-router") 

# Русские строки
TEXT_TO_BE_PAID_RUB = "К оплате - {amount}₽ ⬇️"
TEXT_TO_BE_PAID_USD = "К оплате - {amount}$ ⬇️"
TEXT_CHOOSE_TARIFF_CB = "Выберите подходящий тариф ⬇️"
TEXT_ALREADY_USED_TRIAL = "Вы уже использовали пробный период."
TEXT_PROFILE_NOT_FOUND_ERROR = "Ошибка: Ваш профиль не найден. Пожалуйста, попробуйте /start еще раз."
TEXT_TRIAL_SUCCESS = (
    "Благодарим за выбор ❤️\n️\n"
    # "<a href=\"{link}\">Подпишитесь</a>, чтобы не пропустить анонсы ✅\n️\n"
    "Ваша 7-дневная пробная подписка оформлена и доступна в разделе \"Мой профиль 👤\"."
)
TEXT_TRIAL_ACTIVATED_ALERT = "7-дневный пробный период активирован! Проверьте 'Мой профиль 👤'."
TEXT_TRIAL_ACTIVATION_ERROR = "Произошла ошибка при активации пробного периода."
TEXT_SELECT_PAYMENT_METHOD = "Выберите способ оплаты ⬇️"
TEXT_HAS_ACTIVE_PAID_SUB = "У вас уже есть активная платная подписка до {expire_date}."

# Тексты ответов для FAQ (сокращенные для alerts)
FAQ_A1_TEXT = "Нажмите кнопку «7 дней бесплатно» в главном меню (команда /start). Бот предоставит вам бесплатный тестовый доступ на 7 дней. Тест можно получить один раз.»"
FAQ_A2_TEXT = "Наш VPN можно использовать на Android, iOS, Windows и macOS.\nПосле оформления подписки (включая тестовую) информация для подключения будет доступна в разделе «Мой профиль 👤»."
FAQ_A3_TEXT = "Актуальные тарифы и цены смотрите в разделе «Купить подписку 🛒» в главном меню.\nСейчас доступны подписки на 1, 3 и 6 месяцев."
FAQ_A4_TEXT = "Инфо о подписке (тип, статус, дата окончания)\nнаходится в разделе «Мой профиль 👤»."
FAQ_A5_TEXT = "Мы не ограничиваем трафик.\nСтремимся обеспечить макс. скорость и стабильное соединение для всех."
FAQ_A6_TEXT = "Если у вас возникли трудности или вопросы,\nвоспользуйтесь кнопкой «Поддержка ❤️» в главном меню.\nМы постараемся помочь."
FAQ_A7_TEXT = "VPN (шифрованный туннель) защищает ваш интернет-трафик от посторонних.\nЭто повышает безопасность в общественных Wi-Fi и скрывает действия от провайдера.\nМы используем надёжные протоколы."
FAQ_A8_TEXT = "Приложения:\nAndroid: v2rayTun, Husi, AmneziaVPN\niOS/macOS: Streisand, FoXray, v2Box\nWindows: v2rayN, Nekoray\nИнструкции в разделе «Мой профиль 👤»."

@router.callback_query(F.data.startswith("pay_kassa_"))
async def callback_payment_method_select(callback: CallbackQuery):
    data = callback.data.replace("pay_kassa_", "")
    if data not in goods.get_callbacks():
        await callback.answer()
        return
    
    good = goods.get(data)
    result = await yookassa.create_payment(
        callback.from_user.id, 
        data, 
        callback.message.chat.id, 
    )

    months = good.get('months')
    if months == 1:
        duration_text = "1 месяц"
    elif months in [3, 6]:
        duration_text = f"{months} месяцев"
    else:
        duration_text = f"{months} дней" # для тестового периода

    text = f"""   *Вы собираетесь купить:* 

📋 {good['title']}
💸 **стоимость:** {result['amount']}₽

**Описание:**
✅ Прокси на **{duration_text}** (протокол Vless).
•  **Локация:**
 🇳🇱 Нидерланды. 

🔒 Полная анонимность, не собираем данные пользователей.
🔑 **1 ключ = 1 устройство.**

⚠️ Для подключения к RU сайтам и приложениям без VPN см. инструкцию (доступна по сслыке после оплаты).

👇 **Введите ваш email для получения чека**"""

    await callback.message.edit_text(
        text,
        reply_markup=get_pay_keyboard(result['url']),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("pay_crypto_"))
async def callback_payment_method_select(callback: CallbackQuery):
    data = callback.data.replace("pay_crypto_", "")
    if data not in goods.get_callbacks():
        await callback.answer()
        return

    good = goods.get(data)
    result = await cryptomus.create_payment(
        callback.from_user.id, 
        data, 
        callback.message.chat.id, 
    )

    months = good.get('months')
    if months == 1:
        duration_text = "1 месяц"
    elif months in [3, 6]:
        duration_text = f"{months} месяцев"
    else:
        duration_text = f"{months} дней" # для тестового периода

    text = f"""✨ *Вы собираетесь купить подписку* ✨

📋 **Подписка:** {good['title']}
💰 **Цена:** {result['amount']}$

---

**Описание:**

✅ Прокси на **{duration_text}** (протокол Vless).
🌍 **Локация:** 🇳🇱 Нидерланды.

🔒 Полная анонимность, не собираем данные пользователей.
🔑 **1 ключ = 1 устройство.**

---

👇 **Выберите способ оплаты:**"""
    await callback.message.edit_text(
        text,
        reply_markup=get_pay_keyboard(result['url']),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "buy_subscription_action")
async def handle_buy_subscription_action(callback: CallbackQuery):
    await callback.answer() 
    await callback.message.answer(
        TEXT_CHOOSE_TARIFF_CB, 
        reply_markup=get_buy_menu_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "try_free_action")
async def handle_try_free_action(callback: CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    # 1. Проверить наличие активной платной подписки в Marzban
    marzban_profile = await marzban_api.get_marzban_profile(user_id)
    db_profile = await get_marzban_profile_db(user_id) # Нужен для определения, была ли подписка тестовой

    if marzban_profile and marzban_profile.get('status') == 'active':
        is_currently_test_sub_in_db = db_profile.test if db_profile else False
        
        # Если подписка активна в Marzban и в нашей БД она НЕ помечена как тестовая,
        # значит это активная ПЛАТНАЯ подписка.
        if not is_currently_test_sub_in_db:
            expire_timestamp = marzban_profile.get('expire')
            expire_date_str = "неизвестной даты"
            if expire_timestamp:
                expire_date_str = datetime.fromtimestamp(expire_timestamp).strftime("%d.%m.%Y %H:%M")
            
            await callback.answer(TEXT_HAS_ACTIVE_PAID_SUB.format(expire_date=expire_date_str), show_alert=True, parse_mode="HTML")
            return
        # Если же активна в Marzban, но в нашей БД она тестовая, то позволяем логике ниже (проверка already_had_test) решить.
        # Это может произойти, если пользователь нажал "попробовать бесплатно" во время уже активного триала.

    # 2. Если нет активной платной подписки, продолжаем текущую логику
    already_had_test_flag = await can_get_test_sub(user_id)
    if already_had_test_flag:
        # Дополнительная проверка: если already_had_test_flag is True, но в Marzban нет активной подписки
        # или она истекла, то это действительно "уже использовал".
        # Если же в Marzban активная (и по логике выше это должна быть тестовая), то эта проверка уже покрыта.
        # В целом, can_get_test_sub должен быть главным индикатором того, был ли тест ИСПОЛЬЗОВАН.
        await callback.answer(TEXT_ALREADY_USED_TRIAL, show_alert=True)
        return

    # db_user_profile уже получен выше как db_profile
    if not db_profile: # Если профиля нет даже в локальной БД (маловероятно после /start, но для надежности)
        await marzban_api.create_user_if_not_exists_in_local_db(user_id, callback.from_user.full_name, callback.from_user.username)
        db_profile = await get_marzban_profile_db(user_id)
        if not db_profile:
             await callback.answer(TEXT_PROFILE_NOT_FOUND_ERROR, show_alert=True)
             return

    try:
        try:
            trial_duration_hours = int(glv.config.get('PERIOD_LIMIT', 7 * 24))
        except ValueError:
            trial_duration_hours = 7 * 24
            print(f"[WARNING] PERIOD_LIMIT in .env is not a valid integer. Defaulting to {trial_duration_hours} hours for trial.")

        marzban_user_data = await marzban_api.generate_test_subscription(
            str(db_profile.tg_id), 
            custom_hours=trial_duration_hours
        )
        
        # Устанавливаем флаг, что тестовая подписка была использована
        await update_test_subscription_state(user_id, is_test=True) # is_test=True, так как это выдача триала

        final_text = TEXT_TRIAL_SUCCESS.format(
             link=glv.config['PANEL_GLOBAL'] + marzban_user_data['subscription_url']
        )

        await glv.bot.send_message(chat_id, final_text, parse_mode="HTML") # Добавим parse_mode для ссылки
        await callback.answer(TEXT_TRIAL_ACTIVATED_ALERT, show_alert=True)

    except Exception as e:
        error_message_for_user = TEXT_TRIAL_ACTIVATION_ERROR
        if callback.message:
             await callback.message.answer(error_message_for_user)
        await callback.answer(error_message_for_user, show_alert=True)
        
        import traceback
        print(f"Error in handle_try_free_action for user {user_id}: {str(e)}")
        print(traceback.format_exc())

@router.callback_query(lambda c: c.data in goods.get_callbacks())
async def callback_payment_select_good(callback: CallbackQuery):
    # await callback.message.delete() # Убираем удаление
    good = goods.get(callback.data)
    # Заменяем answer на edit_text
    await callback.message.edit_text(
        text=TEXT_SELECT_PAYMENT_METHOD, 
        reply_markup=get_payment_keyboard(good)
    )
    await callback.answer()

# Обработчики для кнопок FAQ
@router.callback_query(F.data == "faq_q1")
async def handle_faq_q1(callback: CallbackQuery):
    await callback.answer(FAQ_A1_TEXT, show_alert=True)

@router.callback_query(F.data == "faq_q2")
async def handle_faq_q2(callback: CallbackQuery):
    await callback.answer(FAQ_A2_TEXT, show_alert=True)

@router.callback_query(F.data == "faq_q3")
async def handle_faq_q3(callback: CallbackQuery):
    await callback.answer(FAQ_A3_TEXT, show_alert=True)

@router.callback_query(F.data == "faq_q4")
async def handle_faq_q4(callback: CallbackQuery):
    await callback.answer(FAQ_A4_TEXT, show_alert=True)

@router.callback_query(F.data == "faq_q5")
async def handle_faq_q5(callback: CallbackQuery):
    await callback.answer(FAQ_A5_TEXT, show_alert=True)

@router.callback_query(F.data == "faq_q6")
async def handle_faq_q6(callback: CallbackQuery):
    await callback.answer(FAQ_A6_TEXT, show_alert=True)

@router.callback_query(F.data == "faq_q7")
async def handle_faq_q7(callback: CallbackQuery):
    await callback.answer(FAQ_A7_TEXT, show_alert=True)

@router.callback_query(F.data == "faq_q8")
async def handle_faq_q8(callback: CallbackQuery):
    await callback.answer(FAQ_A8_TEXT, show_alert=True)

def register_callbacks(dp: Dispatcher):
    dp.include_router(router)
