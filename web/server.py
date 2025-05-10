# web/server.py

import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
import os
import json
import base64

import aiohttp_jinja2
import jinja2
from aiohttp import web
import httpx

from tgbot.services.db import get_user
from marzban.client import get_raw_link
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
    # Endpoint для выдачи полного V2Ray-конфига с inbound на 53 и DNS
    app.router.add_get("/route/{token}", handle_full_config)

    return app

@aiohttp_jinja2.template("dashboard.html")
async def handle_instruction(request: web.Request):
    try:
        user_id = int(request.query.get("user_id", "0"))
        record  = await get_user(user_id) or {}
        now     = datetime.now(timezone.utc)

        # Начальные значения
        plan    = "отсутствует"
        raw_end = None
        link    = None
        raw_uri = None
        route_b64 = None

        # Платная подписка
        if record.get("sub_id") and record.get("subscription_end"):
            end_dt = datetime.fromisoformat(record["subscription_end"].rstrip('Z'))
            if end_dt > now:
                plan    = "платная"
                raw_end = end_dt
                link    = await safe_link(record["sub_id"])
                raw_uri = await safe_raw_link(record["sub_id"])

        # Пробная подписка
        elif record.get("is_trial") and record.get("trial_end"):
            end_dt = datetime.fromisoformat(record["trial_end"].rstrip('Z'))
            if end_dt > now:
                plan    = "пробная"
                raw_end = end_dt
                link    = await safe_link(record["trial_sub_id"])
                raw_uri = await safe_raw_link(record["trial_sub_id"])

        end_date  = raw_end.strftime("%d.%m.%Y") if raw_end else "—"
        days_left = (raw_end - now).days if raw_end else None
        user_key  = record.get("vless_key", "")

        # Генерим Base64 для import_route
        if link:
            token = link.rstrip("/").split("/")[-1].split("?")[0]
            cfg_url = f"{request.scheme}://{request.host}/route/{token}"
            # Собираем JSON-пакет с указанием route_url
            payload = json.dumps({"route_url": cfg_url}).encode()
            route_b64 = base64.urlsafe_b64encode(payload).decode().rstrip("=")

        logger.info("DEBUG link for user_id=%s → %r", user_id, link)

        return {
            "request":    request,
            "user_id":    user_id,
            "plan":       plan,
            "end_date":   end_date,
            "days_left":  days_left,
            "link":       link,
            "raw_uri":    raw_uri,
            "route_b64":  route_b64,
            "user_key":   user_key,
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
        client     = await marzban_client.get_client()
        httpx_cli  = client.get_async_httpx_client()
        resp       = await httpx_cli.get(f"/api/user/{sub_id}/usage")
        resp.raise_for_status()
        data       = resp.json()
        usages     = data.get("usages", [])
        used       = sum(item.get("used_traffic", 0) for item in usages)
        total      = 100 * 1024**3
    except Exception as e:
        logger.error(f"Error fetching usage for {sub_id}: {e}")
        total = 0

    return web.json_response({"usedBytes": used, "totalBytes": total, "endDate": end_date})

async def handle_full_config(request: web.Request):
    """
    Отдаёт полный V2Ray-конфиг:
      - inbound на 53/udp (dokodemo-door)
      - outbound 'dns' (DoH + резервные IP)
      - outbound 'proxy' (вся подписка из Marzban)
      - routing: порт 53 -> dns, всё остальное -> proxy
    """
    token = request.match_info["token"]
    # 1) Получаем оригинальную подписку
    async with httpx.AsyncClient() as cli:
        resp = await cli.get(f"http://free_vpn_bot_marzban:8002/sub/{token}")
    resp.raise_for_status()
    arr = resp.json()  # список V2Ray-конфигов

    # 2) Собираем outbounds
    outbounds = [{
        "tag": "dns",
        "protocol": "dns",
        "settings": {
            "servers": [
                "https://dns.comss.one/dns-query",
                "1.1.1.1",
                "8.8.8.8"
            ]
        }
    }]
    # добавляем те же конфиги как proxy-outbound
    for cfg in arr:
        proxy_cfg = {
            "tag": "proxy",
            **cfg
        }
        outbounds.append(proxy_cfg)

    # 3) Формируем полный конфиг
    full_cfg = {
        "inbounds": [
            {
                "port": 53,
                "protocol": "dokodemo-door",
                "settings": {
                    "network": "udp",
                    "followRedirect": True
                }
            }
        ],
        "outbounds": outbounds,
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                {"type": "field", "port": "53", "outboundTag": "dns"},
                {"type": "field", "outboundTag": "proxy"}
            ]
        }
    }

    return web.json_response(full_cfg)

async def safe_link(sub_id: str) -> str | None:
    """Обёртка для get_subscription_url — старая логика."""
    try:
        return await get_raw_link(sub_id)
    except Exception:
        return None

async def safe_raw_link(sub_id: str) -> str | None:
    """Если нужно raw-vless URI отдельно."""
    try:
        return await get_raw_link(sub_id)
    except Exception:
        return None

if __name__ == "__main__":
    logger.info("Starting instruction server on 0.0.0.0:8080")
    web.run_app(create_app(), host="0.0.0.0", port=8080)
