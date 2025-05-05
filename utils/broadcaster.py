import asyncio
import logging
from typing import Union

from aiogram import Bot, exceptions
from aiogram.types import InlineKeyboardMarkup

async def send_message(
        bot: Bot,
        user_id: Union[int, str],
        text: str,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup = None,
) -> bool:
    """
    Safe message sender.

    :param bot: Bot instance.
    :param user_id: user id. If str, must contain only digits.
    :param text: message text.
    :param disable_notification: disable notification or not.
    :param reply_markup: reply markup.
    :return: True on success.
    """
    try:
        await bot.send_message(
            user_id,
            text,
            disable_notification=disable_notification,
            reply_markup=reply_markup,
        )
    except exceptions.TelegramBadRequest as e:
        logging.error(f"BadRequest sending to [ID:{user_id}]: {e}")
    except exceptions.TelegramForbiddenError:
        logging.error(f"Forbidden sending to [ID:{user_id}]: bot was blocked")
    except exceptions.TelegramRetryAfter as e:
        logging.error(f"Flood limit exceeded for [ID:{user_id}], retry in {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
        return await send_message(bot, user_id, text, disable_notification, reply_markup)
    except exceptions.TelegramNetworkError as e:
        logging.error(f"Network error sending to [ID:{user_id}]: {e}")
    except exceptions.TelegramAPIError as e:
        logging.exception(f"API error sending to [ID:{user_id}]: {e}")
    except Exception as e:
        logging.exception(f"Unexpected error sending to [ID:{user_id}]: {e}")
    else:
        logging.info(f"Message sent successfully to [ID:{user_id}]")
        return True
    return False

async def broadcast(
        bot: Bot,
        users: list[Union[int, str]],
        text: str,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup = None,
) -> int:
    """
    Simple broadcaster.

    :param bot: Bot instance.
    :param users: List of user IDs.
    :param text: message text.
    :param disable_notification: disable notification or not.
    :param reply_markup: reply markup.
    :return: number of successful sends.
    """
    count = 0
    for user_id in users:
        if await send_message(bot, user_id, text, disable_notification, reply_markup):
            count += 1
        await asyncio.sleep(0.05)  # limit ~20 msgs/sec
    logging.info(f"{count} messages successfully sent.")
    return count
