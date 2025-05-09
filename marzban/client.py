# client.py
import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
from typing import List, Optional

import httpcore
import httpx

from marzban_api_client.api.user.add_user             import asyncio_detailed as add_user
from marzban_api_client.api.user.get_user             import asyncio_detailed as get_user_api
from marzban_api_client.api.user.delete_expired_users import asyncio_detailed as delete_expired_users

from marzban_api_client.models import (
    UserCreate,
    UserCreateProxies,
    UserCreateInbounds,
    UserDataLimitResetStrategy,
    UserResponse,
)
from marzban_api_client.types import Response

logger = logging.getLogger(__name__)

# ─── Шаблон прокси/инбаундов ────────────────────────────────────────────────────
proxies = UserCreateProxies.from_dict({"vless": {"flow": "xtls-rprx-vision"}})
inbounds = UserCreateInbounds.from_dict({"VLESS TCP": True})

def expire_timestamp(dt: datetime) -> int:
    """Переводим datetime → UNIX-timestamp (секунды)."""
    return int(dt.timestamp())

async def create_user(
    sub_id: str,
    expire: datetime,
    data_limit: int = 0,
    reset_strategy: UserDataLimitResetStrategy = UserDataLimitResetStrategy.NO_RESET,
) -> bool:
    """POST /api/user — создаёт нового пользователя."""
    from loader import marzban_client

    body = UserCreate(
        username=sub_id,
        data_limit=data_limit,
        data_limit_reset_strategy=reset_strategy,
        expire=expire_timestamp(expire),
        inbounds=inbounds,
        proxies=proxies,
    )
    logger.info("📤 create_user body: %s", json.dumps(body.to_dict(), ensure_ascii=False))

    client = await marzban_client.get_client()
    try:
        resp: Response = await add_user(client=client, body=body)
    except (httpcore.RemoteProtocolError, httpx.RemoteProtocolError) as e:
        logger.error("❌ create_user: connection dropped: %s", e)
        return False
    except httpx.HTTPError as e:
        logger.error("❌ create_user: HTTP error: %s", e)
        return False
    except Exception:
        logger.exception("❌ create_user: unexpected error")
        return False

    logger.info("📥 create_user response: %s", resp.status_code)
    return resp.status_code == 200

async def get_marz_user(sub_id: str) -> UserResponse:
    """GET /api/user/{sub_id} — получает данные пользователя."""
    from loader import marzban_client

    client = await marzban_client.get_client()
    resp = await get_user_api(sub_id, client=client)
    return resp.parsed

async def get_raw_link(sub_id: str) -> str:
    """Из UserResponse.links возвращает первую VLESS-ссылку."""
    data = await get_marz_user(sub_id)
    for link in data.links:
        if link.startswith("vless://"):
            return link
    raise RuntimeError("No VLESS link")

async def get_user_links(sub_id: str) -> str:
    """Формирует текстовый список всех VLESS-ссылок."""
    data = await get_marz_user(sub_id)
    blocks: List[str] = []
    for link in data.links:
        if not link.startswith("vless://"):
            continue
        proto = parse_qs(urlparse(link).query).get("type", [""])[0]
        blocks.append(f"Протокол: <b>VLESS {proto}</b>\n<pre>{link}</pre>")
    return "\n\n".join(blocks)

async def get_subscription_url(sub_id: str) -> str:
    """
    Возвращает HTTP-URL подписки, по которому клиенты подтягивают JSON-массив
    конфигов вместе с трафиком и датой окончания.
    """
    from loader import marzban_client

    client = await marzban_client.get_client()
    base = client.base_url.rstrip("/")
    return f"{base}/api/v1/client/subscribe?token={sub_id}"

async def extend_user(
    sub_id: str,
    new_expire: datetime,
    data_limit: Optional[int] = None,
    reset_strategy: UserDataLimitResetStrategy = UserDataLimitResetStrategy.NO_RESET,
) -> bool:
    """PUT /api/user/{sub_id} — продлевает срок подписки и при необходимости обновляет лимит."""
    from loader import marzban_client

    expire_ts = expire_timestamp(new_expire)
    logger.info(f">>> extend_user: PUT /api/user/{sub_id} expire={expire_ts}")

    body_dict = {"expire": expire_ts}
    if data_limit is not None:
        body_dict["data_limit"] = data_limit
        body_dict["data_limit_reset_strategy"] = reset_strategy

    client = await marzban_client.get_client()
    httpx_client = client.get_async_httpx_client()

    try:
        resp = await httpx_client.put(
            url=f"/api/user/{sub_id}",
            json=body_dict,
        )
    except (httpcore.RemoteProtocolError, httpx.RemoteProtocolError) as e:
        logger.error("❌ extend_user: connection dropped: %s", e)
        return False
    except httpx.HTTPError as e:
        logger.error("❌ extend_user: HTTP error: %s", e)
        return False
    except Exception:
        logger.exception("❌ extend_user: unexpected error")
        return False

    body = await resp.aread()
    logger.info(f">>> extend_user response: {resp.status_code} – {body!r}")
    return resp.status_code == 200

async def delete_users() -> None:
    """DELETE /api/users/expired — удаляет всех просроченных."""
    from loader import marzban_client

    client = await marzban_client.get_client()
    try:
        resp: Response = await delete_expired_users(
            expired_after=datetime(1970, 1, 1, tzinfo=timezone.utc),
            expired_before=datetime.now(timezone.utc),
            client=client,
        )
        logger.info("📤 delete_users response: %s", resp.parsed)
    except Exception:
        logger.exception("❌ delete_users: unexpected error")
