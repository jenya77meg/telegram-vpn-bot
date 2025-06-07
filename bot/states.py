from aiogram.fsm.state import StatesGroup, State

class EmailState(StatesGroup):
    wait_for_email = State()
    confirm_email = State() 