from sqlalchemy import Column, BigInteger, String, Boolean

from db.base import Base

class VPNUsers(Base):
    __tablename__ = "vpnusers"

    id = Column(BigInteger, primary_key=True, unique=True, autoincrement=True)
    tg_id = Column(BigInteger, unique=True)
    vpn_id = Column(String(64), default="")
    test = Column(Boolean, default=False)
    display_name = Column(String(255), default="")
    telegram_username = Column(String(255), default="")
    email = Column(String(255), nullable=True)

class Sellers(Base):
    __tablename__ = "sellers"

    id = Column(BigInteger, primary_key=True, unique=True, autoincrement=True)
    name = Column(String(255))
    tg_id = Column(BigInteger, unique=True)
    referral_code = Column(String(255), unique=True)
    balance = Column(BigInteger, default=0)

class Referrals(Base):
    __tablename__ = "referrals"

    id = Column(BigInteger, primary_key=True, unique=True, autoincrement=True)
    user_tg_id = Column(BigInteger, unique=True)
    seller_id = Column(BigInteger)

class Payouts(Base):
    __tablename__ = "payouts"

    id = Column(BigInteger, primary_key=True, unique=True, autoincrement=True)
    seller_id = Column(BigInteger, nullable=False)
    amount = Column(BigInteger, nullable=False) # in kopecks/cents
    payout_date = Column(String(64), default="") # Using string for simplicity, will store ISO format date
    comment = Column(String(512), nullable=True)

class CPayments(Base):
    __tablename__ = "crypto_payments"

    id = Column(BigInteger, primary_key=True, unique=True, autoincrement=True)
    tg_id = Column(BigInteger)
    lang = Column(String(64))
    payment_uuid = Column(String(64))
    order_id = Column(String(64))
    chat_id = Column(BigInteger)
    callback = Column(String(64))

class YPayments(Base):
    __tablename__ = "yookassa_payments"

    id = Column(BigInteger, primary_key=True, unique=True, autoincrement=True)
    tg_id = Column(BigInteger)
    lang = Column(String(64))
    payment_id = Column(String(64))
    chat_id = Column(BigInteger)
    callback = Column(String(64))