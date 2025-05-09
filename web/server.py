# web/server.py
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
import os

import aiohttp_jinja2
import jinja2
from aiohttp import web

from tgbot.services.db import get_user
from marzban.client import get_raw_link, get_marz_user
from loader import marzban_client

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

# CORS middleware
@web.middleware
async def cors_middleware(request: web.Request, handler):
    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

# Логирование запросов
@web.middleware
async def log_requests(request: web.Request, handler):
    logger.info(f"--> {request.method} {request.path_qs}")
    resp = await handler(request)
    logger.info(f"<-- {resp.status} {request.method} {request.path_qs}")
    return resp


def create_app() -> web.Application:
    app = web.Application(debug=True, middlewares=[cors_middleware, log_requests])
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)))
    app.router.add_static('/assets/', path=str(BASE_DIR / 'assets'), show_index=False)
    app.router.add_get("/instruction", handle_instruction)
    app.router.add_get("/api/vpn/usage", handle_usage)
    return app


@aiohttp_jinja2.template("dashboard.html")
async def handle_instruction(request: web.Request):
    try:
        user_id = int(request.query.get("user_id", "0"))
        record  = await get_user(user_id) or {}
        now     = datetime.now(timezone.utc)

        plan    = "отсутствует"
        raw_end = None
        link    = None
        raw_uri = None

        # Платная подписка
        if record.get("sub_id") and record.get("subscription_end"):
            end_dt = datetime.fromisoformat(record["subscription_end"].rstrip('Z'))
            if end_dt > now:
                plan    = "платная"
                raw_end = end_dt
                link    = await safe_subscription_link(record["sub_id"])
                raw_uri = await safe_link(record["sub_id"])

        # Пробная подписка
        elif record.get("is_trial") and record.get("trial_end"):
            end_dt = datetime.fromisoformat(record["trial_end"].rstrip('Z'))
            if end_dt > now:
                plan    = "пробная"
                raw_end = end_dt
                link    = await safe_subscription_link(record["trial_sub_id"])
                raw_uri = await safe_link(record["trial_sub_id"])

        # Отладочное логирование
        logger.info("DEBUG subscription link for user_id=%s → %r", user_id, link)

        end_date  = raw_end.strftime("%d.%m.%Y") if raw_end else "—"
        days_left = (raw_end - now).days if raw_end else None
        user_key  = record.get("vless_key", "")

        return {
            "request":   request,
            "user_id":   user_id,
            "plan":      plan,
            "end_date":  end_date,
            "days_left": days_left,
            "link":      link,
            "raw_uri":   raw_uri,
            "user_key":  user_key,
        }

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return web.Response(
            text=f"500 Internal Server Error\n\n{e}\n\n{tb}",
            status=500,
            content_type="text/plain"
        )


async def handle_usage(request: web.Request):
    try:
        user_id = int(request.query.get("user_id"))
    except (TypeError, ValueError):
        raise web.HTTPBadRequest(text="invalid user_id")

    record = await get_user(user_id) or {}
    logger.debug(f"record keys for user {user_id}: {list(record.keys())}")

    sub_id = record.get("sub_id") or record.get("trial_sub_id")
    if not sub_id:
        return web.json_response({"usedBytes": 0, "totalBytes": 0, "endDate": None})

    used = 0
    total = 0
    end_date = record.get("subscription_end") or record.get("trial_end")

    try:
        client = await marzban_client.get_client()
        httpx_client = client.get_async_httpx_client()
        resp = await httpx_client.get(f"/api/user/{sub_id}/usage")
        resp.raise_for_status()
        data = resp.json()
        usages = data.get("usages", [])
        used = sum(item.get("used_traffic", 0) for item in usages)
        total = 100 * 1024**3
    except Exception as e:
        logger.error(f"Error fetching usage for {sub_id}: {e}")
        total = 0

    return web.json_response({"usedBytes": used, "totalBytes": total, "endDate": end_date})


async def get_subscription_token(sub_id: str) -> str:
    """
    Берёт из модели пользователя готовый токен подписки,
    такой же, как в ссылке и QR-коде панели.
    """
    user = await get_marz_user(sub_id)
    return user.subscription_url


async def get_subscription_url(sub_id: str) -> str:
    """
    Берём готовую ссылку подписки из панели (полный URL!) и возвращаем её «как есть».
    """
    # это уже полноценный URL вида https://host/.../sub/<token>
    subscription_url = await get_subscription_token(sub_id)

    # если вдруг вернулся относительный токен (без https://), склеиваем
    if not subscription_url.startswith("http"):
        prefix = os.getenv("XRAY_SUBSCRIPTION_URL_PREFIX", "").rstrip("/")
        path   = os.getenv("XRAY_SUBSCRIPTION_PATH", "").lstrip("/").rstrip("/")
        return f"{prefix}/{path}/{subscription_url}"

    # иначе — просто отдаём уже полный URL
    return subscription_url


async def safe_subscription_link(sub_id: str) -> str | None:
    try:
        return await get_subscription_url(sub_id)
    except Exception:
        return None

async def safe_link(sub_id: str) -> str | None:
    try:
        return await get_raw_link(sub_id)
    except Exception:
        return None


if __name__ == "__main__":
    logger.info("Starting instruction server on 0.0.0.0:8080")
    web.run_app(create_app(), host="0.0.0.0", port=8080)
