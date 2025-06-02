from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

BTN_TEXT_RENEW_SUB = "Продлить подписку"
BTN_TEXT_BUY_SUB_PROFILE = "Купить подписку"

def get_profile_actions_keyboard(
    show_renew: bool = False, 
    show_buy: bool = False
) -> InlineKeyboardMarkup | None:
    builder = InlineKeyboardBuilder()
    
    if show_renew:
        builder.row(InlineKeyboardButton(text=BTN_TEXT_RENEW_SUB, callback_data="buy_subscription_action"))
        
    if show_buy:
        # Если кнопка "Продлить" уже есть, и это по сути то же самое (ведет на одно меню покупки),
        # то, возможно, не стоит добавлять "Купить", если только тексты/контекст не должны отличаться.
        # Пока оставим возможность добавления обеих, если оба флага True.
        builder.row(InlineKeyboardButton(text=BTN_TEXT_BUY_SUB_PROFILE, callback_data="buy_subscription_action"))
        
    # Проверяем, были ли добавлены какие-либо кнопки.
    # builder.export() вернет список рядов кнопок. Если он пуст, значит кнопок нет.
    if not builder.export(): 
        return None
        
    return builder.as_markup() 