from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from tgbot.services.profile_service import build_profile_content
from tgbot.utils.keyboards import build_main_menu_kb

router = Router()

@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """
    Хендлер для команды /profile: показывает профиль пользователя.
    """
    user_id = message.from_user.id
    name = message.from_user.first_name or message.from_user.username or "друг"
    text, inline_kb, reply_kb = await build_profile_content(user_id, name)

    await message.answer(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=inline_kb,
    )
    await message.answer(
        "Выберите действие:",
        reply_markup=reply_kb,
    )

@router.message(F.text == "◀️ Назад")
async def back_to_main_from_profile(message: Message):
    """
    Возвращает пользователя в главное меню при нажатии кнопки Назад.
    """
    main_kb = await build_main_menu_kb(message.from_user.id)
    await message.answer("Что вы хотите сделать?", reply_markup=main_kb)
