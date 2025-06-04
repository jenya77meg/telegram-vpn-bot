from yookassa import Configuration
from yookassa import Payment

from db.methods import add_yookassa_payment
from utils import goods
import glv

if glv.config['YOOKASSA_SHOPID'] and glv.config['YOOKASSA_TOKEN']:
    Configuration.configure(glv.config['YOOKASSA_SHOPID'], glv.config['YOOKASSA_TOKEN'])

async def create_payment(tg_id: int, callback: str, chat_id: int, user_email: str = None) -> dict:
    good = goods.get(callback)
    receipt_item_description = f"Доступ к сервису {glv.config['SHOP_NAME']} - {good['title']}"

    bot_username = (await glv.bot.get_me()).username
    return_url_for_payment = f"https://t.me/{bot_username}"

    payment_params = {
        "amount": {
            "value": good['price']['ru'],
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": return_url_for_payment
        },
        "capture": True,
        "description": f"Оплата подписки на сервис {glv.config['SHOP_NAME']} (товар: {good['title']})",
        "save_payment_method": False,
        "receipt": {
            "customer": {
                "email": user_email if user_email else glv.config['EMAIL']
            },
            "items": [
                {
                    "description": receipt_item_description,
                    "quantity": "1",
                    "amount": {
                        "value": good['price']['ru'],
                        "currency": "RUB"
                    },
                    "vat_code": "1"
                },
            ]
        }
    }
    
    resp = Payment.create(payment_params)

    await add_yookassa_payment(tg_id, callback, chat_id, "ru", resp.id)
    return {
        "url": resp.confirmation.confirmation_url,
        "amount": resp.amount.value,
        "payment_id": resp.id
    }