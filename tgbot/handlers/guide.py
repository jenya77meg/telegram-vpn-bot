# tgbot/handlers/guide.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

router = Router()

# 1) Состояния для шагов инструкции
class GuideStates(StatesGroup):
    STEP = State()

# 2) Контент инструкции — список шагов
STEPS = [
    "🟢 Шаг 1: Установите приложение AmneziaVPN из App Store / Google Play.",
    "🟢 Шаг 2: Запустите VPN и нажмите «Добавить новый профиль».",
    "🟢 Шаг 3: Вставьте сюда ваш VLESS-ключ и сохраните.",
    "🟢 Шаг 4: Включите переключатель, чтобы подключиться к VPN.",
    "✅ Готово! Наслаждайтесь безопасным интернетом через наш VPN."
]

# 3) Клавиатура «назад/вперёд»
from aiogram.utils.keyboard import InlineKeyboardBuilder
def build_nav_kb(step: int):
    builder = InlineKeyboardBuilder()
    if step > 0:
        builder.button(text="⬅️ Назад", callback_data=f"guide_back:{step}")
    if step < len(STEPS) - 1:
        builder.button(text="➡️ Вперёд", callback_data=f"guide_next:{step}")
    return builder.as_markup()

# 4) Старт инструкции
@router.message(Command("guide"))
async def cmd_guide_start(message, state: FSMContext):
    await state.set_state(GuideStates.STEP)
    await state.update_data(step=0)
    text = STEPS[0]
    await message.answer(text, reply_markup=build_nav_kb(0))

# 5) Обработчики inline-кнопок
@router.callback_query(F.data.startswith("guide_back:"))
async def cb_guide_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    step = max(0, int(data.get("step", 0)) - 1)
    await state.update_data(step=step)
    await cb.message.edit_text(STEPS[step], reply_markup=build_nav_kb(step))

@router.callback_query(F.data.startswith("guide_next:"))
async def cb_guide_next(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    step = min(len(STEPS) - 1, int(data.get("step", 0)) + 1)
    await state.update_data(step=step)
    await cb.message.edit_text(STEPS[step], reply_markup=build_nav_kb(step))
