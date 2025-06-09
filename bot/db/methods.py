import hashlib

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import insert, select, update, delete

from db.models import YPayments, CPayments, VPNUsers
import glv

engine = create_async_engine(
    glv.config['DB_URL'], 
    echo=True,
    pool_recycle=3600,
    pool_pre_ping=True,
)

async def create_vpn_profile(tg_id: int, first_name: str = "", last_name: str = "", username: str = ""):
    async with engine.connect() as conn:
        sql_query = select(VPNUsers).where(VPNUsers.tg_id == tg_id)
        result: VPNUsers = (await conn.execute(sql_query)).fetchone()
        if result != None:
            return
        hash = hashlib.md5(str(tg_id).encode()).hexdigest()
        
        # Формируем отображаемое имя
        display_name = ""
        if first_name and last_name:
            display_name = f"{first_name} {last_name}".strip()
        elif first_name:
            display_name = first_name
        elif username:
            display_name = f"@{username}"
        else:
            display_name = f"ID: {tg_id}"
        
        print(f"DEBUG: Saving user: tg_id={tg_id}, display_name='{display_name}', telegram_username='{username or ''}'")

        sql_query = insert(VPNUsers).values(
            tg_id=tg_id, 
            vpn_id=hash, 
            display_name=display_name,
            telegram_username=username or ""
        )
        await conn.execute(sql_query)
        await conn.commit()

async def get_marzban_profile_db(tg_id: int) -> VPNUsers:
    async with engine.connect() as conn:
        sql_q = select(VPNUsers).where(VPNUsers.tg_id == tg_id)
        user: VPNUsers = (await conn.execute(sql_q)).fetchone()
    return user

async def get_marzban_profile_by_vpn_id(vpn_id: str):
    async with engine.connect() as conn:
        sql_query = select(VPNUsers).where(VPNUsers.vpn_id == vpn_id)
        result: VPNUsers = (await conn.execute(sql_query)).fetchone()
    return result    

async def get_user_display_info(identifier: str) -> dict:
    """Получает читаемую информацию о пользователе для отображения на сайте.
    Может принимать как vpn_id (MD5), так и tg_id (число в виде строки).
    Если пользователь не найден по tg_id, но идентификатор был числом,
    создает для него профиль в локальной БД."""
    async with engine.connect() as conn:
        # Попытка 1: Поиск по vpn_id (MD5-хеш)
        print(f"DEBUG GUDI: Attempting SELECT by vpn_id: {identifier}")
        sql_query_by_vpn_id = select(VPNUsers).where(VPNUsers.vpn_id == identifier)
        user_by_vpn_id: VPNUsers = (await conn.execute(sql_query_by_vpn_id)).fetchone()
        print(f"DEBUG GUDI: Result SELECT by vpn_id: {'Found' if user_by_vpn_id else 'Not Found'}")

        if user_by_vpn_id:
            return {
                "display_name": user_by_vpn_id.display_name or f"ID: {user_by_vpn_id.tg_id}",
                "telegram_username": user_by_vpn_id.telegram_username or "",
                "tg_id": user_by_vpn_id.tg_id
            }

        # Попытка 2: Если не найден по vpn_id и identifier является числом (потенциальный tg_id)
        if identifier.isdigit():
            tg_id_int = int(identifier)
            print(f"DEBUG GUDI: Attempting SELECT by tg_id: {tg_id_int}")
            sql_query_by_tg_id = select(VPNUsers).where(VPNUsers.tg_id == tg_id_int)
            user_by_tg_id: VPNUsers = (await conn.execute(sql_query_by_tg_id)).fetchone()
            print(f"DEBUG GUDI: Result SELECT by tg_id: {'Found' if user_by_tg_id else 'Not Found'}")

            if user_by_tg_id:
                return {
                    "display_name": user_by_tg_id.display_name or f"ID: {user_by_tg_id.tg_id}",
                    "telegram_username": user_by_tg_id.telegram_username or "",
                    "tg_id": user_by_tg_id.tg_id
                }
            else:
                # Пункт C - "ленивое" создание профиля в локальной БД
                # Пользователь не найден по tg_id, но идентификатор был числом. Создаем профиль.
                new_vpn_id = hashlib.md5(str(tg_id_int).encode()).hexdigest()
                default_display_name = f"ID: {tg_id_int}"
                
                print(f"DEBUG GUDI: Attempting lazy INSERT for tg_id: {tg_id_int}, vpn_id: {new_vpn_id}, display_name: '{default_display_name}'")
                insert_query = insert(VPNUsers).values(
                    tg_id=tg_id_int,
                    vpn_id=new_vpn_id,
                    display_name=default_display_name,
                    telegram_username=""
                )
                await conn.execute(insert_query)
                print(f"DEBUG GUDI: Lazy INSERT executed for tg_id: {tg_id_int}. Attempting COMMIT.")
                await conn.commit()
                print(f"DEBUG GUDI: COMMIT successful for lazy INSERT tg_id: {tg_id_int}")
                return {
                    "display_name": default_display_name,
                    "telegram_username": "",
                    "tg_id": tg_id_int
                }

        # Попытка 3: identifier не числовой и не найден как vpn_id
        # Это, скорее всего, имя пользователя, заданное вручную в Marzban (не TG ID).
        # Или какой-то другой идентификатор, который не является ни tg_id, ни vpn_id из нашей БД.
        print(f"DEBUG: User not found by vpn_id or tg_id. Identifier: '{identifier}'. Returning identifier as display_name.")
        return {"display_name": identifier, "telegram_username": "", "tg_id": None}

async def can_get_test_sub(tg_id: int) -> bool:
    async with engine.connect() as conn:
        sql_query = select(VPNUsers).where(VPNUsers.tg_id == tg_id)
        result: VPNUsers = (await conn.execute(sql_query)).fetchone()
    # Добавим проверку на None, чтобы избежать ошибки, если пользователя нет в БД
    return result.test if result else False 

async def update_test_subscription_state(tg_id: int, is_test: bool):
    async with engine.connect() as conn:
        sql_q = update(VPNUsers).where(VPNUsers.tg_id == tg_id).values(test=is_test) # Используем переданное значение
        await conn.execute(sql_q)
        await conn.commit()

async def add_yookassa_payment(tg_id: int, callback: str, chat_id: int, lang_code: str, payment_id) -> dict:
    async with engine.connect() as conn:
        sql_q = insert(YPayments).values(tg_id=tg_id, payment_id=payment_id, chat_id=chat_id, callback=callback, lang=lang_code)
        await conn.execute(sql_q)
        await conn.commit()

async def add_cryptomus_payment(tg_id: int, callback: str, chat_id: int, lang_code: str, data) -> dict:
    async with engine.connect() as conn:
        sql_q = insert(CPayments).values(tg_id=tg_id, payment_uuid=data['order_id'], order_id=data['order_id'], chat_id=chat_id, callback=callback, lang=lang_code)
        await conn.execute(sql_q)
        await conn.commit()

async def get_yookassa_payment(payment_id) -> YPayments:
    async with engine.connect() as conn:
        sql_q = select(YPayments).where(YPayments.payment_id == payment_id)
        payment: YPayments = (await conn.execute(sql_q)).fetchone()
    return payment

async def get_cryptomus_payment(order_id) -> CPayments:
    async with engine.connect() as conn:
        sql_q = select(CPayments).where(CPayments.order_id == order_id)
        payment: CPayments = (await conn.execute(sql_q)).fetchone()
    return payment

async def delete_payment(payment_id):
    async with engine.connect() as conn:
        sql_q = delete(YPayments).where(YPayments.payment_id == payment_id)
        await conn.execute(sql_q)
        await conn.commit()
        sql_q = delete(CPayments).where(CPayments.payment_uuid == payment_id)
        await conn.execute(sql_q)
        await conn.commit()

async def get_user_email(tg_id: int) -> str | None:
    user = await get_marzban_profile_db(tg_id)
    return user.email if user else None

async def update_user_email(tg_id: int, email: str):
    async with engine.connect() as conn:
        sql_q = update(VPNUsers).where(VPNUsers.tg_id == tg_id).values(email=email)
        await conn.execute(sql_q)
        await conn.commit()

async def get_all_vpn_users_tg_id() -> list[int]:
    async with engine.connect() as conn:
        query = select(VPNUsers.tg_id)
        result = (await conn.execute(query)).scalars().all()
    return result

# --- Seller and Referral Methods ---

from .models import Sellers, Referrals, Payouts
from sqlalchemy import func

async def add_seller(name: str, tg_id: int, referral_code: str):
    async with engine.connect() as conn:
        sql_query = insert(Sellers).values(
            name=name,
            tg_id=tg_id,
            referral_code=referral_code
        )
        await conn.execute(sql_query)
        await conn.commit()

async def remove_seller(referral_code: str):
    async with engine.connect() as conn:
        sql_query = delete(Sellers).where(Sellers.referral_code == referral_code)
        await conn.execute(sql_query)
        await conn.commit()

async def get_seller_by_referral_code(referral_code: str) -> Sellers | None:
    async with engine.connect() as conn:
        sql_query = select(Sellers).where(Sellers.referral_code == referral_code)
        result = (await conn.execute(sql_query)).fetchone()
    return result

async def get_all_sellers() -> list[Sellers]:
    async with engine.connect() as conn:
        sql_query = select(Sellers)
        result = (await conn.execute(sql_query)).fetchall()
    return result

async def add_referral(user_tg_id: int, seller_id: int):
    async with engine.connect() as conn:
        sql_query = insert(Referrals).values(
            user_tg_id=user_tg_id,
            seller_id=seller_id
        )
        await conn.execute(sql_query)
        await conn.commit()

async def get_referral_by_user(user_tg_id: int) -> Referrals | None:
    async with engine.connect() as conn:
        sql_query = select(Referrals).where(Referrals.user_tg_id == user_tg_id)
        result = (await conn.execute(sql_query)).fetchone()
    return result

async def get_seller_by_id(seller_id: int) -> Sellers | None:
    async with engine.connect() as conn:
        sql_query = select(Sellers).where(Sellers.id == seller_id)
        result = (await conn.execute(sql_query)).fetchone()
    return result

async def update_seller_balance(seller_id: int, amount: int):
    async with engine.connect() as conn:
        current_balance_query = select(Sellers.balance).where(Sellers.id == seller_id)
        current_balance = (await conn.execute(current_balance_query)).scalar_one()
        
        new_balance = current_balance + amount

        update_query = update(Sellers).where(Sellers.id == seller_id).values(balance=new_balance)
        await conn.execute(update_query)
        await conn.commit()

async def get_seller_by_tg_id(tg_id: int) -> Sellers | None:
    async with engine.connect() as conn:
        sql_query = select(Sellers).where(Sellers.tg_id == tg_id)
        result = (await conn.execute(sql_query)).fetchone()
    return result

async def count_referrals_for_seller(seller_id: int) -> int:
    async with engine.connect() as conn:
        query = select(func.count()).select_from(Referrals).where(Referrals.seller_id == seller_id)
        result = (await conn.execute(query)).scalar_one()
    return result

async def update_seller_details(current_referral_code: str, field: str, new_value) -> bool:
    async with engine.connect() as conn:
        # Check if the new referral code is already taken, if we're changing it
        if field == 'referral_code':
            existing = await get_seller_by_referral_code(new_value)
            if existing:
                return False # New code is already in use

        update_query = update(Sellers).where(Sellers.referral_code == current_referral_code).values({field: new_value})
        await conn.execute(update_query)
        await conn.commit()
    return True

async def create_payout(seller_id: int, amount_kopecks: int, comment: str | None) -> bool:
    async with engine.connect() as conn:
        async with conn.begin(): # Start a transaction
            # 1. Check if balance is sufficient
            current_balance_query = select(Sellers.balance).where(Sellers.id == seller_id)
            current_balance = (await conn.execute(current_balance_query)).scalar_one_or_none()

            if current_balance is None or current_balance < amount_kopecks:
                return False # Insufficient balance

            # 2. Subtract from seller's balance
            new_balance = current_balance - amount_kopecks
            update_balance_query = update(Sellers).where(Sellers.id == seller_id).values(balance=new_balance)
            await conn.execute(update_balance_query)

            # 3. Record the payout
            from datetime import datetime
            payout_record_query = insert(Payouts).values(
                seller_id=seller_id,
                amount=amount_kopecks,
                payout_date=datetime.utcnow().isoformat(),
                comment=comment
            )
            await conn.execute(payout_record_query)
        
        # The transaction is automatically committed if the block completes without exceptions
    return True

async def get_payouts_for_seller(seller_id: int) -> list[Payouts]:
    async with engine.connect() as conn:
        query = select(Payouts).where(Payouts.seller_id == seller_id).order_by(Payouts.payout_date.desc())
        result = (await conn.execute(query)).fetchall()
    return result