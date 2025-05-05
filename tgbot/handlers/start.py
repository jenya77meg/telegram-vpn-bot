from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from tgbot.keyboards.inline import inline_start_kb
from tgbot.keyboards.reply import start_kb
from tgbot.utils.keyboards import build_main_menu_kb  # ваш новый импорт

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    name = message.from_user.first_name or message.from_user.username or "друг"

    # Приветствие со статичной reply‑клавиатурой (если нужна)
    await message.answer(f"Привет, {name}! 👋", reply_markup=start_kb)

    # Контент с inline‑кнопками
    await message.answer(
        "Самый быстрый, доступный и удобный VPN.\n"
        "✅ 7 дней бесплатного пробного периода.\n"
        "🕹 Быстрое подключение к VPN.\n"
        "🔒 Отсутствие лимитов трафика.\n"
        "🌐 Высокая скорость и стабильное подключение.\n\n"
        "Нажмите на одну из кнопок ниже, чтобы продолжить:",
        reply_markup=inline_start_kb,
        disable_web_page_preview=True,
    )

    # Динамическое главное меню с датой окончания подписки
    main_kb = await build_main_menu_kb(message.from_user.id)
    await message.answer("Что вы хотите сделать?", reply_markup=main_kb)
