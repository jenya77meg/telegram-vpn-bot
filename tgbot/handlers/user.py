import uuid
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import CallbackQuery

from loader import bot
from marzban.client import create_user as mb_create, get_raw_link, get_user_links
from tgbot.services.db import get_user, create_user, activate_trial, clear_trial_history
from tgbot.utils.keyboards import build_main_menu_kb  # динамическое главное меню

user_router = Router()

@user_router.callback_query(F.data == "free_trial_inline")
async def free_inline(cb: CallbackQuery):
    """Активирует пробник, если с последнего прошло ≥ 4 месяцев."""
    await cb.answer()
    user_id = cb.from_user.id
    main_kb = await build_main_menu_kb(user_id)

    # создаём профиль при необходимости
    await create_user(user_id)
    record = await get_user(user_id) or {}

    # 0.5) Если trial-аккаунт удалён в Marzban — сбросить всю историю trial
    if record.get("trial_sub_id"):
        try:
            await get_user_links(record["trial_sub_id"])
        except Exception:
            # аккаунт удалён — сбрасываем все поля trial
            await clear_trial_history(user_id)
            # обновляем локальную запись из БД
            record = await get_user(user_id) or {}


    # 1) Если уже есть активный пробный — сразу уведомляем
    if record.get("is_trial") and record.get("trial_end"):
        try:
            end_dt = datetime.fromisoformat(record["trial_end"])
            if end_dt > datetime.now(timezone.utc):
                return await cb.message.answer(
                    f"У вас уже есть активный пробный период до {end_dt.strftime('%d.%m.%Y')}.",
                    reply_markup=main_kb,
                )
        except ValueError:
            pass

    # 2) Проверка активной платной подписки
    if record.get("sub_id") and record.get("subscription_end") and not record.get("is_trial", 0):
        end_dt = datetime.fromisoformat(record["subscription_end"])
        if end_dt > datetime.now(timezone.utc):
            return await cb.message.answer(
                f"У вас уже есть активная платная подписка до {end_dt.strftime('%d.%m.%Y')}. Пробный период недоступен.",
                reply_markup=main_kb,
            )

    # 3) Проверка кулдауна (120 дней с trial_last)
    last_iso = record.get("trial_last")
    if last_iso:
        last_dt = datetime.fromisoformat(last_iso)
        if datetime.now(timezone.utc) - last_dt < timedelta(days=120):
            return await cb.message.answer(
                "❌ Вы уже активировали бесплатный пробный период за последние 4 месяца.",
                reply_markup=main_kb,
            )

    # 4) Создаём пробный ключ
    sub_id = str(uuid.uuid4())
    expire_dt = datetime.now(timezone.utc) + timedelta(days=7)
    if not await mb_create(sub_id, expire_dt):
        return await cb.message.answer(
            "❌ Не удалось выдать пробный ключ. Попробуйте позже.",
            reply_markup=main_kb,
        )
    raw_link = await get_raw_link(sub_id)
    await activate_trial(user_id, sub_id, raw_link, expire_dt.isoformat())

    return await cb.message.answer(
        f"🎉 Бесплатный пробный период на 7 дней активирован!\n"
        f"🔑 Ваш VLESS‑ключ до {expire_dt.strftime('%d.%m.%Y')}:\n"
        f"<pre lang=\"vpn\">{raw_link}</pre>",
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=main_kb,
    )
