# tgbot/handlers/vpn.py

import uuid
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from loader import bot
from marzban.client import create_user as mb_create, get_raw_link, extend_user
from tgbot.services.db import create_user, get_user, update_user_subscription, clear_user_subscription
from tgbot.keyboards.reply import durations_kb, payment_kb, profile_kb
from tgbot.utils.keyboards import build_main_menu_kb  # <-- импорт динамического меню

vpn_router = Router()

class NavStates(StatesGroup):
    MAIN = State()
    PERIOD = State()
    PAYMENT = State()


async def _create_or_get_key(message: Message, days: int):
    user_id = message.from_user.id
    # строим динамическое главное меню
    main_kb = await build_main_menu_kb(user_id)

    now = datetime.now(timezone.utc)
    await create_user(user_id)
    record = await get_user(user_id)

    # 1‑A. Есть действующий платный ключ и days == 0
    if record and record.get("sub_id") and record.get("subscription_end"):
        end_dt = datetime.fromisoformat(record["subscription_end"])
        is_trial = bool(record.get("is_trial", 0))

        try:
            live_link = await get_raw_link(record["sub_id"])
        except Exception:
            await clear_user_subscription(user_id)
            record = await get_user(user_id)
        else:
            if end_dt > now and days == 0:
                return await message.answer(
                    f"🔑 Ваш VLESS‑ключ до {end_dt.strftime('%d.%m.%Y')}:\n"
                    f"<pre lang=\"vpn\">{live_link}</pre>",
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=main_kb,
                )
            if end_dt > now and not is_trial and days > 0:
                new_expire = end_dt + timedelta(days=days)
                if await extend_user(record["sub_id"], new_expire):
                    new_link = await get_raw_link(record["sub_id"])
                    await update_user_subscription(
                        user_id,
                        record["sub_id"],
                        record["vless_key"],
                        new_expire.isoformat(),
                    )
                    return await message.answer(
                        f"🔑 Подписка продлена до {new_expire.strftime('%d.%m.%Y')}:\n"
                        f"<pre lang=\"vpn\">{new_link}</pre>",
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                        reply_markup=main_kb,
                    )

    # 2. Активный пробник (days == 0)
    if days == 0 and record and record.get("trial_sub_id") and record.get("trial_end"):
        trial_end = datetime.fromisoformat(record["trial_end"])
        if trial_end > now:
            try:
                trial_link = await get_raw_link(record["trial_sub_id"])
            except Exception:
                pass
            else:
                return await message.answer(
                    f"🔑 Ваш пробный VLESS‑ключ до {trial_end.strftime('%d.%m.%Y')}:\n"
                    f"<pre lang=\"vpn\">{trial_link}</pre>",
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=main_kb,
                )

    # 3. Нет ключей и days == 0
    if days <= 0:
        return await message.answer(
            "У вас пока нет активной подписки. Нажмите «Купить/продлить VPN», чтобы оформить.",
            reply_markup=main_kb,
        )

    # 4. Создаём нового пользователя (fallback)
    sub_id = str(uuid.uuid4())
    expire_dt = now + timedelta(days=days)
    if not await mb_create(sub_id, expire_dt):
        return await message.reply("❌ Ошибка создания VPN‑пользователя. Попробуйте позже.")

    raw_link = await get_raw_link(sub_id)
    await update_user_subscription(user_id, sub_id, raw_link, expire_dt.isoformat())

    return await message.answer(
        f"🔑 Ваш VLESS‑ключ до {expire_dt.strftime('%d.%m.%Y')}:\n"
        f"<pre lang=\"vpn\">{raw_link}</pre>",
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=main_kb,
    )


@vpn_router.message(Command("vpn"))
async def vpn_main(message: Message, state: FSMContext):
    await state.clear()
    main_kb = await build_main_menu_kb(message.from_user.id)
    await message.answer("Что вы хотите сделать?", reply_markup=main_kb)


@vpn_router.message(F.text == "Купить/продлить VPN")
async def buy_period(message: Message, state: FSMContext):
    await state.set_state(NavStates.PERIOD)
    await message.answer("Выберите срок подписки:", reply_markup=durations_kb)


@vpn_router.message(F.text == "🔑 Мои активные ключи")
async def on_my_keys(message: Message, state: FSMContext):
    await state.clear()
    await _create_or_get_key(message, days=0)


@vpn_router.message(NavStates.PERIOD, F.text.in_(list(durations_kb.keyboard[0] + durations_kb.keyboard[1])))
async def period_chosen(message: Message, state: FSMContext):
    days_map = {btn.text: d for btn, d in zip(
        durations_kb.keyboard[0] + durations_kb.keyboard[1],
        [30, 60, 90, 180]
    )}
    days = days_map.get(message.text)
    if days is None:
        return
    await state.update_data(days=days)
    await state.set_state(NavStates.PAYMENT)
    await message.answer("Выберите способ оплаты:", reply_markup=payment_kb)


@vpn_router.message(NavStates.PAYMENT, F.text.in_(["💳 Перевод", "⭐️ Телеграм‑звёзды"]))
async def do_payment(message: Message, state: FSMContext):
    data = await state.get_data()
    days = data.get("days", 0)
    await state.clear()

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


@vpn_router.callback_query(F.data == "vpn")
async def on_vpn_callback(cb: CallbackQuery, state: FSMContext):
    await state.set_state(NavStates.PERIOD)
    await cb.answer()
    await cb.message.answer("Выберите срок подписки:", reply_markup=durations_kb)


@vpn_router.message(F.text == "🔷 Главное меню")
async def main_menu_btn(message: Message, state: FSMContext):
    await state.clear()
    main_kb = await build_main_menu_kb(message.from_user.id)
    await message.answer("Что вы хотите сделать?", reply_markup=main_kb)


@vpn_router.message(F.text == "📖 Инструкция")
async def send_instruction(message: Message, state: FSMContext):
    await state.clear()
    main_kb = await build_main_menu_kb(message.from_user.id)
    await message.answer(
        "1. Установите AmneziaVPN\n"
        "2. Вставьте ваш VLESS‑ключ в приложение\n"
        "3. Подключайтесь и пользуйтесь интернетом через VPN",
        reply_markup=main_kb,
    )


@vpn_router.message(F.text == "❓ Помощь")
async def send_help(message: Message, state: FSMContext):
    await state.clear()
    main_kb = await build_main_menu_kb(message.from_user.id)
    await message.answer(
        "Обратитесь к @noskillol — он поможет!",
        reply_markup=main_kb,
    )
