import aiosqlite
from datetime import datetime, timezone
from typing import Optional, Dict, Any

DB_PATH = "bot.db"

async def init_db() -> None:
    """Создаём таблицу users + «миграции» при запуске"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY);"
        )
        for column, ctype in (
            ("sub_id", "TEXT"),
            ("vless_key", "TEXT"),
            ("subscription_end", "TEXT"),
            ("is_trial", "INTEGER DEFAULT 0"),
            ("trial_last", "TEXT"),
            ("trial_sub_id", "TEXT"),
            ("trial_end", "TEXT"),
        ):
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {column} {ctype}")
            except aiosqlite.OperationalError:
                pass
        await db.commit()

async def create_user(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users(user_id) VALUES(?)",
            (user_id,),
        )
        await db.commit()

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT user_id, sub_id, vless_key, subscription_end,
                   is_trial, trial_last, trial_sub_id, trial_end
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

async def update_user_subscription(
    user_id: int,
    sub_id: str,
    vless_key: str,
    subscription_end: str
) -> None:
    """Записывает / продлевает платную подписку и сбрасывает trial-поля."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET sub_id           = ?,
                vless_key        = ?,
                subscription_end = ?,
                is_trial         = 0,
                trial_sub_id     = NULL,
                trial_end        = NULL
            WHERE user_id = ?
            """,
            (sub_id, vless_key, subscription_end, user_id),
        )
        await db.commit()

async def activate_trial(
    user_id: int,
    sub_id: str,
    key: str,
    end_iso: str
) -> None:
    """Сохраняет новый пробный период, не трогая платные поля."""
    now_iso = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET is_trial     = 1,
                trial_last   = ?,
                trial_sub_id = ?,
                trial_end    = ?
            WHERE user_id = ?
            """,
            (now_iso, sub_id, end_iso, user_id),
        )
        await db.commit()

async def clear_user_subscription(user_id: int, trial: bool = False) -> None:
    """
    Очищает платные или пробные поля.
      - trial=True — только is_trial, trial_sub_id, trial_end
      - trial=False — только sub_id, vless_key, subscription_end
    """
    async with aiosqlite.connect(DB_PATH) as db:
        if trial:
            # сбрасываем только пробные поля, сохраняя дату trial_last
            await db.execute(
                """
                UPDATE users
                SET is_trial     = 0,
                    trial_sub_id = NULL,
                    trial_end    = NULL
                WHERE user_id = ?
                """,
                (user_id,),
            )
        else:
            # сбрасываем только платные поля
            await db.execute(
                """
                UPDATE users
                SET sub_id           = NULL,
                    vless_key        = NULL,
                    subscription_end = NULL
                WHERE user_id = ?
                """,
                (user_id,),
            )
        await db.commit()

async def get_all_users_with_sub():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT user_id, sub_id, subscription_end,
                   is_trial, trial_last, trial_sub_id, trial_end
            FROM users
            WHERE sub_id IS NOT NULL
            """
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

async def clear_trial_history(user_id: int) -> None:
    """
    Полностью сбрасывает все поля пробного периода:
      is_trial, trial_sub_id, trial_end, trial_last.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET is_trial     = 0,
                trial_sub_id = NULL,
                trial_end    = NULL,
                trial_last   = NULL
            WHERE user_id = ?
            """,
            (user_id,),
        )
        await db.commit()
