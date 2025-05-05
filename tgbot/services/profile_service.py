from datetime import datetime, timezone
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

from tgbot.services.db import get_user, clear_user_subscription
from marzban.client import get_raw_link
from tgbot.keyboards.reply import profile_kb

async def build_profile_content(
    user_id: int,
    name: str
) -> tuple[str, InlineKeyboardMarkup | None, ReplyKeyboardMarkup]:
    """
    Составляет текст профиля и подготавливает inline-клавиатуру для продления при необходимости.
    Возвращает: (profile_text, inline_markup, reply_markup)
    """
    record = await get_user(user_id) or {}
    now = datetime.now(timezone.utc)

    plan = "отсутствует"
    raw_end = None

    # Платная подписка
    if record.get("sub_id") and record.get("subscription_end"):
        try:
            end_dt = datetime.fromisoformat(record["subscription_end"])
            if end_dt > now:
                await get_raw_link(record["sub_id"])
                plan = "платная"
                raw_end = record["subscription_end"]
                if record.get("is_trial"):
                    await clear_user_subscription(user_id, trial=True)
                    record = await get_user(user_id) or {}
        except Exception:
            await clear_user_subscription(user_id)
            record = await get_user(user_id) or {}

    # Пробная подписка
    if plan == "отсутствует" and record.get("is_trial") and record.get("trial_sub_id") and record.get("trial_end"):
        try:
            end_dt = datetime.fromisoformat(record["trial_end"])
            if end_dt > now:
                await get_raw_link(record["trial_sub_id"])
                plan = "пробная"
                raw_end = record["trial_end"]
            else:
                await clear_user_subscription(user_id, trial=True)
                record = await get_user(user_id) or {}
        except Exception:
            await clear_user_subscription(user_id, trial=True)
            record = await get_user(user_id) or {}

    # Форматирование даты и дней
    days_left = None
    end_str = "—"
    days_str = ""
    if raw_end:
        try:
            end_dt = datetime.fromisoformat(raw_end)
            days_left = (end_dt.replace(tzinfo=timezone.utc) - now).days
            end_str = end_dt.strftime("%d.%m.%Y")
            days_str = f"(через {days_left} дн.)" if days_left >= 0 else "(просрочена)"
        except ValueError:
            end_str = "неизвестно"

    # Сборка текста
    info_text = (
        f"📋 Ваш профиль, {name}:\n\n"
        f"🔸 Тип подписки: <b>{plan}</b>\n"
        f"🔸 Окончание: <b>{end_str}</b> {days_str}\n"
        f"🔸 ID пользователя: <code>{user_id}</code>"
    )

    # Inline-кнопка «Продлить» при необходимости
    builder = InlineKeyboardBuilder()
    inline_kb: InlineKeyboardMarkup | None = None
    if days_left is not None and days_left < 10 and plan != "отсутствует":
        builder.button(text="Продлить", callback_data="vpn")
        builder.adjust(1)
        inline_kb = builder.as_markup()

    # Возвращаем текст, inline- и reply-клавиатуры
    return info_text, inline_kb, profile_kb
