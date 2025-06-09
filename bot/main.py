import asyncio
import logging
import sys
import time
from pathlib import Path
import os

from aiogram import Bot, Dispatcher, enums
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from handlers.commands import register_commands
from handlers.messages import register_messages
from handlers.callbacks import register_callbacks
from middlewares.db_check import DBCheck
from app.routes import check_crypto_payment, check_yookassa_payment, get_user_display_info_endpoint
from tasks import register
import glv
from utils.marzban_api import panel

# --- для healthcheck ---
from db.methods import engine as db_engine
from sqlalchemy import select
# -----------------------

# --- для автосоздания таблиц ---
from sqlalchemy.ext.asyncio import create_async_engine
from db.base import Base
from db.models import VPNUsers, CPayments, YPayments
# ---------------------------------

glv.bot = Bot(glv.config['BOT_TOKEN'], parse_mode=enums.ParseMode.HTML)
glv.storage = MemoryStorage()
glv.dp = Dispatcher(storage=glv.storage)
app = web.Application()

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def health_check(request):
    """
    Эндпоинт для мониторинга состояния сервиса (Uptime Kuma).
    Проверяет доступность:
    1. Telegram Bot API
    2. Базы данных
    3. Marzban Panel API
    """
    services_status = {
        "telegram": "ok",
        "database": "ok",
        "marzban": "ok"
    }
    is_healthy = True

    # 1. Проверка Telegram API
    try:
        await glv.bot.get_me()
    except Exception as e:
        logging.error(f"Health check failed (Telegram): {e}")
        services_status["telegram"] = "error"
        is_healthy = False

    # 2. Проверка базы данных
    try:
        async with db_engine.connect() as conn:
            await conn.execute(select(1))
    except Exception as e:
        logging.error(f"Health check failed (Database): {e}")
        services_status["database"] = "error"
        is_healthy = False

    # 3. Проверка Marzban API
    try:
        # get_token() - синхронная функция, поэтому просто вызываем
        panel.get_token()
    except Exception as e:
        logging.error(f"Health check failed (Marzban): {e}")
        services_status["marzban"] = "error"
        is_healthy = False

    status_code = 200 if is_healthy else 503
    return web.json_response(services_status, status=status_code)

# --- Раздельные health checks ---

async def health_check_telegram(request):
    """Проверяет только доступность Telegram Bot API."""
    try:
        await glv.bot.get_me()
        return web.Response(status=200, text="OK")
    except Exception as e:
        logging.error(f"Health check failed (Telegram): {e}")
        return web.Response(status=503, text="Service Unavailable")

async def health_check_database(request):
    """Проверяет только доступность Базы данных."""
    try:
        async with db_engine.connect() as conn:
            await conn.execute(select(1))
        return web.Response(status=200, text="OK")
    except Exception as e:
        logging.error(f"Health check failed (Database): {e}")
        return web.Response(status=503, text="Service Unavailable")

async def health_check_marzban(request):
    """Проверяет только доступность Marzban Panel API."""
    try:
        panel.get_token()
        return web.Response(status=200, text="OK")
    except Exception as e:
        logging.error(f"Health check failed (Marzban): {e}")
        return web.Response(status=503, text="Service Unavailable")

async def on_startup(bot: Bot):
    # 0) Автоматически создаём все таблицы из Base.metadata
    engine = create_async_engine(
        glv.config['DB_URL'], 
        echo=True,
        pool_recycle=3600,
        pool_pre_ping=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1) Устанавливаем вебхук
    print("=== on_startup: deleting old webhook ===")
    await bot.delete_webhook(drop_pending_updates=True)
    print("=== on_startup: setting new webhook ===")
    await bot.set_webhook(f"{glv.config['WEBHOOK_URL']}/webhook")
    print("=== on_startup: webhook set ===")

    # 2) Регистрируем фоновые задачи
    asyncio.create_task(register())

def setup_routers():
    register_commands(glv.dp)
    register_messages(glv.dp)
    register_callbacks(glv.dp)

def setup_middlewares():
    # Удаляем все, что связано с i18n
    # locales_path = Path(__file__).parent / 'locales'
    # default_locale = 'ru'
    # domain = 'bot'

    # print(f"[I18N_DEBUG] Attempting to set up I18n.")
    # print(f"[I18N_DEBUG] Locales path: {locales_path}")
    # print(f"[I18N_DEBUG] Default locale: {default_locale}")
    # print(f"[I18N_DEBUG] Domain: {domain}")

    # ru_mo_file_path = locales_path / default_locale / 'LC_MESSAGES' / f"{domain}.mo"
    # print(f"[I18N_DEBUG] Expected Russian .mo file path: {ru_mo_file_path}")
    # if os.path.exists(ru_mo_file_path):
    #     print(f"[I18N_DEBUG] Russian .mo file EXISTS at: {ru_mo_file_path}")
    # else:
    #     print(f"[I18N_DEBUG] Russian .mo file DOES NOT EXIST at: {ru_mo_file_path} <--- PROBLEM HERE?")

    # i18n = I18n(path=locales_path, default_locale=default_locale, domain=domain)
    # i18n_middleware = SimpleI18nMiddleware(i18n=i18n)
    # i18n_middleware.setup(glv.dp)
    
    # Оставляем только DBCheck middleware
    glv.dp.message.middleware(DBCheck())

async def main():
    # Ждём, пока Marzban API поднимется
    print("⏳ Waiting for Marzban API...")
    while True:
        try:
            panel.get_token()
            print("✅ Marzban API is ready!")
            break
        except Exception as e:
            print(f"…still waiting: {e}")
            time.sleep(2)

    # Настройка роутеров и мидлварей
    setup_routers()
    setup_middlewares()
    glv.dp.startup.register(on_startup)

    # Платёжные вебхуки
    app.router.add_post("/cryptomus_payment", check_crypto_payment)
    app.router.add_post("/yookassa_payment", check_yookassa_payment)
    
    # API для получения информации о пользователе
    app.router.add_get("/api/user_info/{vpn_id}", get_user_display_info_endpoint)

    # Healthchecks для Uptime Kuma
    app.router.add_get("/healthz", health_check) # Общий
    app.router.add_get("/healthz/telegram", health_check_telegram)
    app.router.add_get("/healthz/database", health_check_database)
    app.router.add_get("/healthz/marzban", health_check_marzban)

    # Телеграм-вебхук
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=glv.dp,
        bot=glv.bot,
    )
    webhook_requests_handler.register(app, path="/webhook")

    # Остальная инициализация
    setup_application(app, glv.dp, bot=glv.bot)

    # Запуск веб-сервера
    await web._run_app(app, host="0.0.0.0", port=glv.config['WEBHOOK_PORT'])

if __name__ == "__main__":
    asyncio.run(main())
