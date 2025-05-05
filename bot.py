import asyncio
import logging

from aiogram import Bot, Dispatcher, F, exceptions
from aiogram.enums import ChatType
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import load_config
config = load_config()

from tgbot.handlers import routers_list
from tgbot.middlewares.flood import ThrottlingMiddleware
from utils import broadcaster

# Подключаем инструкционный веб-сервер
from web.server import create_app

logger = logging.getLogger(__name__)

async def on_startup(bot: Bot):
    # 1. Попытка уведомить администратора
    try:
        await broadcaster.broadcast(bot, [config.tg_bot.admin_id], "Бот запущен")
    except Exception as e:
        logger.warning(f"Не удалось отправить стартовое уведомление: {e}")

    # 2. Попытка зарегистрировать команды
    try:
        await register_commands(bot)
    except Exception as e:
        logger.warning(f"Не удалось зарегистрировать команды: {e}")

    # 3. Установка вебхука (если включён)
    if config.webhook.use_webhook:
        try:
            await bot.set_webhook(
                f"https://{config.webhook.domain}{config.webhook.url}webhook"
            )
        except Exception as e:
            logger.warning(f"Не удалось установить вебхук: {e}")

async def register_commands(bot: Bot):
    commands = [
        BotCommand(command='start',   description='Главное меню 🏠'),
        BotCommand(command='help',    description='Помощь'),
        BotCommand(command='vpn',     description='🔑 Получить ключи'),
    ]
    try:
        await bot.set_my_commands(commands, BotCommandScopeDefault())
    except exceptions.TelegramNetworkError as e:
        logger.warning(f"Сетевая ошибка при установке команд: {e}")
    except exceptions.TelegramAPIError as e:
        logger.error(f"Ошибка API при установке команд: {e}")
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при установке команд: {e}")

def register_global_middlewares(dp: Dispatcher):
    middlewares = [ThrottlingMiddleware()]
    for m in middlewares:
        dp.message.outer_middleware(m)
        dp.callback_query.outer_middleware(m)
    dp.callback_query.outer_middleware(CallbackAnswerMiddleware())
    dp.message.filter(F.chat.type == ChatType.PRIVATE)

async def _start_web_server():
    # Запускаем aiohttp-приложение для /instruction
    app_web = create_app()
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logger.info("Instruction web server started on port 8080")


def main_webhook():
    from loader import bot, dp

    dp.include_routers(*routers_list)
    dp.startup.register(on_startup)
    register_global_middlewares(dp)

    # В режиме webhook API запускается в другом aiohttp-приложении
    app = web.Application()
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path=f'{config.webhook.url}webhook')
    setup_application(app, dp, bot=bot)
    web.run_app(app, host='vpn_bot', port=config.tg_bot.port)

async def main_polling():
    from loader import bot, dp

    dp.include_routers(*routers_list)
    register_global_middlewares(dp)

    # Стартовые задачи
    await on_startup(bot)

    # Запускаем веб-сервер инструкций параллельно
    asyncio.create_task(_start_web_server())

    # Безопасное удаление вебхука
    try:
        await bot.delete_webhook()
    except exceptions.TelegramNetworkError as e:
        logger.warning(f"Сетевая ошибка при удалении вебхука: {e}")
    except Exception as e:
        logger.warning(f"Ошибка при удалении вебхука: {e}")

    # Запуск polling
    await dp.start_polling(bot)

if __name__ == '__main__':
    if config.webhook.use_webhook:
        main_webhook()
    else:
        try:
            asyncio.run(main_polling())
        except (KeyboardInterrupt, SystemExit):
            logger.error("Бот выключен!")
