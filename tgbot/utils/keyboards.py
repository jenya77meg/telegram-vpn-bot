from datetime import datetime, timezone
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from tgbot.services.db import get_user, clear_user_subscription
from marzban.client import get_raw_link

async def build_main_menu_kb(user_id: int) -> ReplyKeyboardMarkup:
    """
    Создаёт главное меню с динамической кнопкой:
      - "Пробный до DD.MM.YYYY" для активного trial
      - "Подписка до DD.MM.YYYY" для активной платной подписки
      - "У вас сейчас нет активной подписки" иначе
    """
    # Получаем актуальные данные пользователя
    user = await get_user(user_id) or {}
    now = datetime.now(timezone.utc)
    label = "У вас сейчас нет активной подписки"

    # 1) Платная подписка
    if user.get("sub_id") and user.get("subscription_end"):
        try:
            end_dt = datetime.fromisoformat(user["subscription_end"])
            if end_dt > now:
                # активная платная подписка
                await get_raw_link(user["sub_id"])
                label = f"Подписка до {end_dt.strftime('%d.%m.%Y')}"
                # очистим trial-поля, если они остались
                if user.get("is_trial"):
                    await clear_user_subscription(user_id, trial=True)
                # сразу возвращаем клавиатуру
                return ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text=label)],
                        [KeyboardButton(text="Купить/продлить VPN"), KeyboardButton(text="Мой профиль")],
                        [KeyboardButton(text="📖 Инструкция"), KeyboardButton(text="❓ Помощь")],
                    ],
                    resize_keyboard=True,
                    one_time_keyboard=False,
                )
            else:
                # платная подписка истекла — сброс платных полей
                await clear_user_subscription(user_id)
        except Exception:
            # недоступный или удалённый ключ — сброс платных полей
            await clear_user_subscription(user_id)
        # обновляем данные после сброса
        user = await get_user(user_id) or {}

    # 2) Пробная подписка (если нет активной платной)
    if user.get("is_trial") and user.get("trial_sub_id") and user.get("trial_end"):
        try:
            end_dt = datetime.fromisoformat(user["trial_end"])
            if end_dt > now:
                # активная пробная подписка
                await get_raw_link(user["trial_sub_id"])
                label = f"Пробный до {end_dt.strftime('%d.%m.%Y')}"
                # возвращаем клавиатуру для пробного
                return ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text=label)],
                        [KeyboardButton(text="Купить/продлить VPN"), KeyboardButton(text="Мой профиль")],
                        [KeyboardButton(text="📖 Инструкция"), KeyboardButton(text="❓ Помощь")],
                    ],
                    resize_keyboard=True,
                    one_time_keyboard=False,
                )
            else:
                # пробная подписка истекла — сброс только trial-полей
                await clear_user_subscription(user_id, trial=True)
        except Exception:
            # недоступный или удалённый ключ — сброс только trial-полей
            await clear_user_subscription(user_id, trial=True)
        # обновляем данные после сброса
        user = await get_user(user_id) or {}

    # 3) Финальная клавиатура с актуальным label
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=label)],
            [KeyboardButton(text="Купить/продлить VPN"), KeyboardButton(text="Мой профиль")],
            [KeyboardButton(text="📖 Инструкция"), KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
