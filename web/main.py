# main.py
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

from client import get_subscription_url  # Ваша функция, возвращающая https://…/sub/<token>

app = FastAPI()

# Указываем папку, где лежат templates/subscription/index.html
BASE_DIR  = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Базовый URL вашего Marzban-сервиса
MARZBAN_API_BASE = os.getenv("MARZBAN_API_BASE", "https://host.almet-sam.ru")

async def fetch_user_info(token: str) -> dict:
    """
    Делает GET https://host.almet-sam.ru/sub/{token}/info
    и возвращает JSON со всеми полями подписки и пользователя.
    """
    url = f"{MARZBAN_API_BASE}/sub/{token}/info"
    async with httpx.AsyncClient() as cli:
        resp = await cli.get(url)
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Subscription not found")
        resp.raise_for_status()
        return resp.json()

@app.get("/sub/{token}", response_class=HTMLResponse)
async def subscription_page(request: Request, token: str):
    # 1) Получаем JSON-инфо о подписке и пользователе
    info = await fetch_user_info(token)

    # Если Pydantic-модель, конвертируем в dict
    if hasattr(info, "dict"):
        info = info.dict()

    # 2) Строим “чистый” HTTPS-URL подписки
    sub_url = await get_subscription_url(token)

    # 3) Отдаём Jinja2-шаблон
    return templates.TemplateResponse(
        "subscription/index.html",
        {
            "request": request,
            "user":    info,    # dict с ключами: username, expire, used_traffic, data_limit, …
            "link":    sub_url, # https://…/sub/<token>
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
