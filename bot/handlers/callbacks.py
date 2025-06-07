from datetime import datetime, timedelta
from typing import Optional

from aiogram import Router, F, types
from aiogram import Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import get_payment_keyboard, get_pay_keyboard, get_buy_menu_keyboard
from utils import goods, yookassa, cryptomus, marzban_api
from db.methods import (
    can_get_test_sub, 
    update_test_subscription_state, 
    get_marzban_profile_db,
    get_user_email,
    update_user_email
)
import glv

router = Router(name="callbacks-router") 

class EmailState(StatesGroup):
    wait_for_email = State()
    confirm_email = State()

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

async def prepare_payment_data(user_id: int, chat_id: int, email: Optional[str], product_callback: str):
    """Готовит данные для сообщения об оплате."""
    good = goods.get(product_callback)
    
    # Сохраняем email в БД, если он предоставлен, или None, если нет.
    await update_user_email(user_id, email)
    
    result = await yookassa.create_payment(
        user_id,
        product_callback,
        chat_id,
        email
    )

    months = good.get('months')
    duration_text = f"{months} {'месяц' if months == 1 else 'месяца' if 1 < months < 5 else 'месяцев'}"

    text = f"""   *Вы собираетесь купить:* 

📋 {good['title']}
💸 **Стоимость:** {result['amount']}₽

**Описание:**
✅ Прокси на **{duration_text}** (протокол Vless).
•  **Локация:**
 🇳🇱 Нидерланды. 

🔒 Полная анонимность, не собираем данные пользователей.
🔑 **1 ключ = 1 устройство.**

⚠️ Для подключения к RU сайтам и приложениям без VPN см. инструкцию (доступна по сслыке после оплаты).
"""
    
    if email:
        text += f"\n\n👇 **Чек будет отправлен на email:** `{email}`"

    return text, get_pay_keyboard(result['url'])


@router.callback_query(F.data.startswith("pay_kassa_"))
async def callback_payment_method_select_kassa(callback: CallbackQuery, state: FSMContext):
    product_callback = callback.data.replace("pay_kassa_", "")
    if product_callback not in goods.get_callbacks():
        await callback.answer()
        return

    await state.update_data(product_callback=product_callback)
    user_email = await get_user_email(callback.from_user.id)

    if user_email:
        # Email есть, просим подтвердить
        await state.set_state(EmailState.confirm_email)
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="✅ Да, всё верно", callback_data="email_confirm_yes"))
        builder.row(InlineKeyboardButton(text="✏️ Указать другой", callback_data="email_confirm_no"))
        await callback.message.edit_text(
            f"Отправим чек на ваш email: `{user_email}`?",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    else:
        # Email нет, просим ввести
        await state.set_state(EmailState.wait_for_email)
        await callback.message.edit_text(
            "Пожалуйста, введите ваш email для отправки чека.\n\n"
            "Если вы не хотите получать чек, напишите «*нет*».",
            parse_mode="Markdown"
        )
        await state.update_data(message_id_to_edit=callback.message.message_id)

    await callback.answer()


@router.callback_query(EmailState.confirm_email, F.data == "email_confirm_yes")
async def process_email_confirm(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    product_callback = user_data.get('product_callback')
    user_email = await get_user_email(callback.from_user.id)
    
    text, keyboard = await prepare_payment_data(
        user_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
        email=user_email,
        product_callback=product_callback
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.clear()


@router.callback_query(EmailState.confirm_email, F.data == "email_confirm_no")
async def process_email_change(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EmailState.wait_for_email)
    await callback.message.edit_text(
        "Хорошо, введите новый email.\n\n"
        "Если вы не хотите получать чек, напишите «*нет*».",
        parse_mode="Markdown"
    )
    await state.update_data(message_id_to_edit=callback.message.message_id)


@router.message(EmailState.wait_for_email, F.text.lower() == "нет")
async def process_email_skip(message: Message, state: FSMContext):
    user_data = await state.get_data()
    product_callback = user_data.get('product_callback')
    message_id_to_edit = user_data.get('message_id_to_edit')
    
    # Сразу удаляем сообщение пользователя
    await message.delete()

    text, keyboard = await prepare_payment_data(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        email=None,
        product_callback=product_callback
    )

    if message_id_to_edit:
        await message.bot.edit_message_text(
            text=text,
            chat_id=message.chat.id,
            message_id=message_id_to_edit,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        # Fallback
        await message.answer(text=text, reply_markup=keyboard, parse_mode="Markdown")
        
    await state.clear()


@router.message(EmailState.wait_for_email, F.text.contains('@'))
async def process_email_input(message: Message, state: FSMContext):
    user_data = await state.get_data()
    product_callback = user_data.get('product_callback')
    message_id_to_edit = user_data.get('message_id_to_edit')
    user_email = message.text

    # Сразу удаляем сообщение пользователя с email'ом
    await message.delete()

    text, keyboard = await prepare_payment_data(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        email=user_email,
        product_callback=product_callback
    )

    if message_id_to_edit:
        await message.bot.edit_message_text(
            text=text,
            chat_id=message.chat.id,
            message_id=message_id_to_edit,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        # Fallback, если вдруг ID сообщения для редактирования не нашелся
        await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    await state.clear()


@router.message(EmailState.wait_for_email)
async def process_invalid_email(message: Message, state: FSMContext):
    await message.answer("Это не похоже на email. Пожалуйста, введите корректный email-адрес или напишите «*нет*».", parse_mode="Markdown")


@router.callback_query(F.data.startswith("pay_crypto_"))
async def callback_payment_method_select(callback: CallbackQuery):
    data = callback.data.replace("pay_crypto_", "")
    if data not in goods.get_callbacks():
        await callback.answer()
        return
    result = await cryptomus.create_payment(
        callback.from_user.id, 
        data, 
        callback.message.chat.id, 
    )
    now = datetime.now()
    expire_date = (now + timedelta(minutes=60)).strftime("%d/%m/%Y, %H:%M")
    good = goods.get(data)
    months = good.get('months')
    duration_text = f"{months} {'месяц' if months == 1 else 'месяца' if 1 < months < 5 else 'месяцев'}"

    await callback.message.edit_text(
        text=f"""✨ *Вы собираетесь купить подписку* ✨

📋 **Подписка:** {good['title']}
💰 **Цена:** {result['amount']}$

---

**Описание:**

✅ Прокси на **{duration_text}** (протокол Vless).
🌍 **Локация:** 🇳🇱 Нидерланды.

🔒 Полная анонимность, не собираем данные пользователей.
🔑 **1 ключ = 1 устройство.**

---

👇 **Выберите способ оплаты:**""",
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
        # Используем значение из конфигурации
        sub_details = await marzban_api.generate_test_subscription(str(user_id), custom_hours=glv.config['PERIOD_LIMIT'])
        if sub_details:
            await update_test_subscription_state(user_id)
            await callback.answer(TEXT_TRIAL_ACTIVATED_ALERT, show_alert=True)
            await callback.message.answer(TEXT_TRIAL_SUCCESS.format(link=glv.config['CHANNEL_LINK']))
        else:
            await callback.answer(TEXT_TRIAL_ACTIVATION_ERROR, show_alert=True)
    except Exception as e:
        print(f"Error in handle_try_free_action: {e}")
        await callback.answer(TEXT_TRIAL_ACTIVATION_ERROR, show_alert=True)
    

@router.callback_query(F.data.startswith("faq_"))
async def process_faq_callback(callback: CallbackQuery):
    question_key = callback.data.split('_')[1]
    
    faq_map = {
        "q1": FAQ_A1_TEXT, "q2": FAQ_A2_TEXT, "q3": FAQ_A3_TEXT,
        "q4": FAQ_A4_TEXT, "q5": FAQ_A5_TEXT, "q6": FAQ_A6_TEXT,
        "q7": FAQ_A7_TEXT, "q8": FAQ_A8_TEXT
    }
    
    answer_text = faq_map.get(question_key, "Ответ не найден.")
    await callback.answer(answer_text, show_alert=True)

@router.callback_query(lambda c: c.data in goods.get_callbacks())
async def callback_payment_select_good(callback: CallbackQuery):
    good = goods.get(callback.data)
    if not good:
        await callback.answer("Товар не найден!", show_alert=True)
        return

    await callback.message.edit_text(
        text=TEXT_SELECT_PAYMENT_METHOD, 
        reply_markup=get_payment_keyboard(good)
    )
    await callback.answer()

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