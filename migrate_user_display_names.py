#!/usr/bin/env python3
"""
Миграция для добавления display_name и telegram_username к существующим пользователям
"""

import asyncio
import sys
sys.path.append('./bot')

from db.models import VPNUsers
from db.methods import engine
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine

async def migrate_existing_users():
    """Обновляем существующих пользователей"""
    print("🔄 Начинаем миграцию существующих пользователей...")
    
    async with engine.connect() as conn:
        # Получаем всех пользователей без display_name
        sql_query = select(VPNUsers).where(
            (VPNUsers.display_name == "") | (VPNUsers.display_name.is_(None))
        )
        result = await conn.execute(sql_query)
        users = result.fetchall()
        
        print(f"📊 Найдено {len(users)} пользователей для обновления")
        
        for user in users:
            # Создаем display_name на основе tg_id
            display_name = f"ID: {user.tg_id}"
            
            # Обновляем пользователя
            update_query = update(VPNUsers).where(
                VPNUsers.id == user.id
            ).values(
                display_name=display_name,
                telegram_username=""
            )
            
            await conn.execute(update_query)
            print(f"✅ Обновлен пользователь {user.tg_id} -> {display_name}")
        
        await conn.commit()
        print("✨ Миграция завершена!")

if __name__ == "__main__":
    asyncio.run(migrate_existing_users()) 