# tgbot/handlers/vpn.py

import uuid
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from config import load_config
config = load_config()
from loader import bot
from marzban.client import create_user as mb_create, get_raw_link, extend_user
from tgbot.services.db import (
    create_user, get_user, update_user_subscription,
    clear_user_subscription, activate_trial
)
from tgbot.utils.keyboards import build_main_menu_kb
from tgbot.keyboards.reply import durations_kb, payment_kb, profile_kb
from tgbot.handlers.vpn_settings import NavStates, _create_or_get_key
from tgbot.services.profile_service import build_profile_content

router = Router()

# Соответствие кнопок и количества дней
DAYS_MAP = {
    "🟡 1 мес – 100₽": 30,
    "🟢 2 мес – 200₽": 60,
    "🔵 3 мес – 300₽": 90,
    "🔶 6 мес – 600₽": 180,
}


@router.message(F.text == "💳 Продлить / Купить")
async def cmd_profile_buy(message: Message, state: FSMContext):
    """Из профиля — возвращаемся в главное меню."""
    await state.clear()
    main_kb = await build_main_menu_kb(message.from_user.id)
    await message.answer("Что вы хотите сделать?", reply_markup=main_kb)


@router.message(Command("vpn"))
async def cmd_vpn(message: Message, state: FSMContext):
    """Команда /vpn — показываем главное меню."""
    await state.clear()
    main_kb = await build_main_menu_kb(message.from_user.id)
    await message.answer("Что вы хотите сделать?", reply_markup=main_kb)


@router.message(F.text == "Мой профиль")
async def cmd_profile_menu(message: Message, state: FSMContext):
    """Переходим в профиль."""
    await state.clear()
    user_id = message.from_user.id
    name = message.from_user.first_name or message.from_user.username or "друг"
    text, inline_kb, reply_kb = await build_profile_content(user_id, name)

    await message.answer(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=inline_kb,
    )
    await message.answer("Выберите действие:", reply_markup=reply_kb)



@router.message(F.text.in_(["Купить/продлить VPN"]))
async def cmd_buy_period(message: Message, state: FSMContext):
    """Запуск FSM для выбора периода."""
    await state.set_state(NavStates.PERIOD)
    await message.answer("Выберите срок подписки:", reply_markup=durations_kb)


@router.message(F.text == "🔑 Мои активные ключи")
async def cmd_keys(message: Message, state: FSMContext):
    """Показываем текущий ключ."""
    await state.clear()
    await _create_or_get_key(message, days=0)


@router.message(NavStates.PERIOD, F.text.in_(list(DAYS_MAP.keys())))
async def cmd_period_chosen(message: Message, state: FSMContext):
    days = DAYS_MAP[message.text]
    await state.update_data(days=days)
    await state.set_state(NavStates.PAYMENT)
    await message.answer("Выберите способ оплаты:", reply_markup=payment_kb)


@router.message(NavStates.PAYMENT, F.text.in_(["💳 Перевод", "⭐️ Телеграм‑звёзды"]))
async def cmd_payment(message: Message, state: FSMContext):
    """Инструкция по оплате и затем выдача/продление ключа."""
    data = await state.get_data()
    days = data.get("days", 0)
    await state.clear()

    # показываем главное меню сразу после оплаты
    main_kb = await build_main_menu_kb(message.from_user.id)

    if message.text == "💳 Перевод":
        await message.answer(
            "Инструкция по оплате переводом: перечислите сумму на карту XXXXXX и пришлите скриншот.",
            reply_markup=main_kb,
        )
    else:
        await message.answer(
            "Оплата звёздами: нажмите «🎁 Подарить звезду» в профиле бота.",
            reply_markup=main_kb,
        )

    await _create_or_get_key(message, days)


@router.callback_query(F.data == "vpn")
async def cb_open_vpn(callback: CallbackQuery, state: FSMContext):
    """Inline‑кнопка «Продлить»."""
    await state.set_state(NavStates.PERIOD)
    await callback.answer()
    await callback.message.answer("Выберите срок подписки:", reply_markup=durations_kb)


@router.callback_query(F.data == "free_trial_inline")
async def cb_free_trial(callback: CallbackQuery, state: FSMContext):
    """Активирует пробный период на 7 дней (кулдаун 4 месяца)."""
    await callback.answer()
    user_id = callback.from_user.id
    main_kb = await build_main_menu_kb(user_id)

    # Создаём профиль при необходимости и получаем запись
    await create_user(user_id)
    record = await get_user(user_id) or {}
    now = datetime.now(timezone.utc)

    # 0) Проверка активного пробного периода
    if record.get("is_trial") and record.get("trial_end"):
        try:
            end_dt = datetime.fromisoformat(record["trial_end"])
            if end_dt > now:
                await callback.message.answer(
                    f"У вас уже есть активный пробный период до {end_dt.strftime('%d.%m.%Y')}.",
                    reply_markup=main_kb,
                )
                return
        except ValueError:
            pass

    # 1) Проверка активной платной подписки
    if record.get("sub_id") and record.get("subscription_end") and not record.get("is_trial", 0):
        try:
            end_dt = datetime.fromisoformat(record["subscription_end"])
            if end_dt > now:
                await callback.message.answer(
                    f"У вас уже есть активная платная подписка до {end_dt.strftime('%d.%m.%Y')}. П�\
лемный период недоступен.",
                    reply_markup=main_kb,
                )
                return
        except ValueError:
            pass

    # 2) Проверка кулдауна (120 дней с trial_last)
    last_iso = record.get("trial_last")
    if last_iso:
        try:
            last_dt = datetime.fromisoformat(last_iso)
            if now - last_dt < timedelta(days=120):
                await callback.message.answer(
                    "❌ Вы уже активировали бесплатный пробный период за последние 4 месяца.",
                    reply_markup=main_kb,
                )
                return
        except ValueError:
            pass

    # 3) Создание пробного ключа
    sub_id = str(uuid.uuid4())
    expire_dt = now + timedelta(days=7)
    if not await mb_create(sub_id, expire_dt):
        await callback.message.answer(
            "❌ Не удалось выдать пробный ключ. Попробуйте позже.",
            reply_markup=main_kb,
        )
        return

    raw_link = await get_raw_link(sub_id)
    await activate_trial(user_id, sub_id, raw_link, expire_dt.isoformat())

    # 4) Отправка нового ключа
    await callback.message.answer(
        f"🎉 Бесплатный пробный период на 7 дней активирован!\n"
        f"🔑 Ваш VLESS‑ключ до {expire_dt.strftime('%d.%m.%Y')}:\n"
        f"<pre lang=\"vpn\">{raw_link}</pre>",
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=main_kb,
    )



# Обработчики кнопки «Назад»
@router.message(NavStates.PAYMENT, F.text == "◀️ Назад")
async def cmd_back_from_payment(message: Message, state: FSMContext):
    await state.set_state(NavStates.PERIOD)
    await message.answer("Выберите срок подписки:", reply_markup=durations_kb)


@router.message(NavStates.PERIOD, F.text == "◀️ Назад")
async def cmd_back_from_period(message: Message, state: FSMContext):
    await state.clear()
    main_kb = await build_main_menu_kb(message.from_user.id)
    await message.answer("Что вы хотите сделать?", reply_markup=main_kb)


@router.message(F.text == "🔷 Главное меню")
async def cmd_main_menu(message: Message, state: FSMContext):
    await state.clear()
    main_kb = await build_main_menu_kb(message.from_user.id)
    await message.answer("Что вы хотите сделать?", reply_markup=main_kb)


@router.message(F.text == "📖 Инструкция")
async def cmd_instruction(message: Message, state: FSMContext):
    user_id = message.from_user.id
    url = f"http://{config.webhook.domain}/instruction?user_id={user_id}"
    await message.answer(
        f"Перейдите по ссылке для инструкции и ваших конфигов:\n{url}",
        disable_web_page_preview=True
    )



@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message, state: FSMContext):
    await state.clear()
    main_kb = await build_main_menu_kb(message.from_user.id)
    await message.answer("Обратитесь к @noskillol — он поможет!", reply_markup=main_kb)
