# web/server.py

import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

import aiohttp_jinja2
import jinja2
from aiohttp import web
import httpx

# Импорт клиента для обращения к Marzban API
from loader import marzban_client

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Пути к директории проекта и шаблонам
BASE_DIR      = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

@web.middleware
async def cors_middleware(request: web.Request, handler):
    resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp

@web.middleware
async def log_requests(request: web.Request, handler):
    logger.info(f"--> {request.method} {request.path_qs}")
    resp = await handler(request)
    logger.info(f"<-- {resp.status} {request.method} {request.path_qs}")
    return resp

@aiohttp_jinja2.template("subscription/index1.html")
async def handle_subscription(request: web.Request):
    """
    Рендерит страницу /sub/{token}.
    Берёт JSON-инфу из Marzban API (/api/user/{token}/info),
    формирует поля для шаблона и отдаёт новый index1.html.
    """
    token = request.match_info.get("token")
    client    = await marzban_client.get_client()
    httpx_cli = client.get_async_httpx_client()

    # 1) Запрашиваем инфо о подписке
    resp = await httpx_cli.get(f"/api/user/{token}/info")
    resp.raise_for_status()
    info = resp.json()
    logger.debug("Raw subscription info for %s: %r", token, info)
    # Проверяем наличие поля subscription_url
    if "subscription_url" in info:
        logger.info("subscription_url found: %s", info["subscription_url"])
    else:
        logger.warning("subscription_url missing in info!")

    now = datetime.now(timezone.utc)

    # 2) Дата окончания и статус подписки
    expire_ts = info.get("expire")
    if expire_ts:
        dt_end    = datetime.fromtimestamp(expire_ts, timezone.utc)
        is_active = dt_end > now
        end_date  = dt_end.strftime("%d.%m.%Y")
        days_left = max((dt_end - now).days, 0)
    else:
        is_active = True
        end_date  = "∞"
        days_left = "—"

    # 3) Трафик
    used  = info.get("used_traffic") or info.get("usedBytes", 0)
    total = info.get("data_limit")    or info.get("totalBytes", 0)

    def fmt_bytes(b: int) -> str:
        for unit in ("B","KB","MB","GB","TB"):
            if b < 1024:
                return f"{b:.2f} {unit}"
            b /= 1024
        return f"{b:.2f} PB"

    used_human  = fmt_bytes(used)
    total_human = fmt_bytes(total)

    # 4) Логика получения link из JSON или статическая конструкция
    link = info.get("subscription_url")
    if not link:
        link = f"{request.scheme}://{request.host}/sub/{token}"

    logger.info("Rendering /sub/%s — link=%r", token, link)

    return {
        "request":     request,
        "user":        info,
        "is_active":   is_active,
        "end_date":    end_date,
        "days_left":   days_left,
        "used_human":  used_human,
        "total_human": total_human,
        "link":        link,
    }

# Остальные маршруты и API...
async def handle_usage(request: web.Request):
    raise web.HTTPNotFound()
async def handle_full_config(request: web.Request):
    raise web.HTTPNotFound()

def create_app() -> web.Application:
    app = web.Application(debug=True, middlewares=[cors_middleware, log_requests])
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)), auto_reload=True)
    app.router.add_static('/assets/', str(BASE_DIR / 'assets'), show_index=False)
    app.router.add_get("/sub/{token}",     handle_subscription)
    return app

if __name__ == "__main__":
    logger.info("Starting server on 0.0.0.0:8080")
    web.run_app(create_app(), host="0.0.0.0", port=8080)
