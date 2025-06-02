from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils import goods

def get_buy_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    base_price_one_month = 0

    all_goods = goods.get()
    if all_goods: # Check if goods list is not empty
        # Attempt to find the 1-month plan to use its price as a base
        # This assumes 'vpn_1_month' is the callback for the 1-month plan
        one_month_good = next((g for g in all_goods if g.get('callback') == "vpn_1_month"), None)
        if one_month_good:
            price_value_one_month = one_month_good['price']
            if isinstance(price_value_one_month, dict):
                base_price_one_month = price_value_one_month.get('ru', 0)
            else:
                base_price_one_month = price_value_one_month
        elif all_goods[0]['callback'] == "vpn_1_month": # Fallback to first item if specific callback not found but it matches
            # This part is less robust, relying on order. Prefer the 'next' method above.
            # Consider removing this fallback or making it more explicit if good structure is guaranteed.
             price_value_one_month = all_goods[0]['price']
             if isinstance(price_value_one_month, dict):
                 base_price_one_month = price_value_one_month.get('ru', 0)
             else:
                 base_price_one_month = price_value_one_month


    for good in all_goods:
        title = good['title']
        current_price_data = good['price']
        months = good.get('months')

        current_price_ru = 0
        if isinstance(current_price_data, dict):
            current_price_ru = current_price_data.get('ru', 0)
        else:
            current_price_ru = current_price_data
        
        button_text = f"{title} - {current_price_ru}₽" 

        if months == 3 and base_price_one_month > 0:
            original_price = base_price_one_month * 3 
            if current_price_ru < original_price: # Check if a discount is effectively applied
                button_text = f"{title} - {current_price_ru}₽ ✨Скидка 10%!✨"
        elif months == 6 and base_price_one_month > 0:
            original_price = base_price_one_month * 6
            if current_price_ru < original_price: # Check if a discount is effectively applied
                button_text = f"{title} - {current_price_ru}₽ ✨Скидка 15%!✨"

        builder.row(InlineKeyboardButton(
            text=button_text,
            callback_data=good['callback'])
        )
    return builder.as_markup()
