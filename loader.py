import asyncio
import logging
import betterlogging as bl
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from utils.logger import APINotificationHandler
from tgbot.services.db import (
    init_db,
    get_all_users_with_sub,
    clear_user_subscription
)
from marzban.init_client import MarzClientCache
from marzban.client import delete_users, get_user_links

# ─── 1. ЗАГРУЗКА КОНФИГА ─────────────────────────────────────────────────────────
config = load_config()

# ─── 2. НАСТРОЙКА ЛОГИРОВАНИЯ ──────────────────────────────────────────────────
def setup_logging():
    log_level = logging.INFO
    bl.basic_colorized_config(level=log_level)
    logging.basicConfig(
        level=log_level,
        format="%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s",
    )
    logger_init = logging.getLogger(__name__)
    api_handler = APINotificationHandler(config.tg_bot.token, config.tg_bot.admin_id)
    api_handler.setLevel(logging.ERROR)
    logger_init.addHandler(api_handler)
    return logger_init

logger = setup_logging()

# ─── 3. СОЗДАНИЕ ОБЪЕКТОВ БОТА ─────────────────────────────────────────────────
bot = Bot(
    token=config.tg_bot.token,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML,
        link_preview_is_disabled=True
    )
)
dp = Dispatcher(storage=MemoryStorage())

# ─── 4. ИНИЦИАЛИЗАЦИЯ БД ПРИ СТАРТЕ ────────────────────────────────────────────
async def _on_startup_db():
    await init_db()
dp.startup.register(_on_startup_db)

# ─── 5. ФОНОВАЯ ЗАДАЧА ОЧИСТКИ ПРОСРОЧЕННЫХ ───────────────────────────────────
async def _periodic_cleanup():
    # дать боту подойти
    await asyncio.sleep(60)
    while True:
        # 5.1 удаляем в Marzban всех просроченных
        try:
            await delete_users()
            logger.info("Marzban: удалены все истёкшие пользователи")
        except Exception as e:
            logger.error(f"Ошибка при удалении в Marzban: {e}")

        # 5.2 синхронизируем локальную БД
        users = await get_all_users_with_sub()
        for row in users:
            uid = row["user_id"]
            sub_id = row["sub_id"]
            try:
                # если акк ещё есть — пропускаем
                await get_user_links(sub_id)
            except Exception:
                # иначе очищаем локально
                await clear_user_subscription(uid)
                logger.info(f"Локально очищена подписка для пользователя {uid}")
        # ждём час
        await asyncio.sleep(3600)

# новый вариант
async def _start_periodic_cleanup():
    # сразу запускаем нашу бесконечную функцию, не блокируя диспетчер
    asyncio.create_task(_periodic_cleanup())

# регистрируем асинхронный стартап‑хендлер
dp.startup.register(_start_periodic_cleanup)

# ─── 6. ИНИЦИАЛИЗАЦИЯ MARZBAN-КЛИЕНТА ──────────────────────────────────────────
base_url = (
    f'https://{config.webhook.domain}/'      # <- если use_webhook=True
    if config.webhook.use_webhook
    else 'https://free_vpn_bot_marzban:8002' # <- локальный вариант
)



marzban_client = MarzClientCache(base_url, config, logger)
