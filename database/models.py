import datetime
from sqlalchemy import (BigInteger, String, Numeric, DateTime, ForeignKey, Integer, Text, Boolean, func, LargeBinary, DECIMAL)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import List, Optional

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = 'users'
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str] = mapped_column(String(32), nullable=True)
    first_name: Mapped[str] = mapped_column(String(64))
    balance: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00)
    registration_date: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    language_code: Mapped[str] = mapped_column(String(10), default='en')
    currency: Mapped[str] = mapped_column(String(5), default='USD')
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    purchased_accounts: Mapped[List["Account"]] = relationship("Account", back_populates="buyer")
    withdrawals: Mapped[List["Withdrawal"]] = relationship("Withdrawal", back_populates="user")

class Country(Base):
    __tablename__ = 'countries'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(10))
    flag_emoji: Mapped[str] = mapped_column(String(5))
    price_per_account: Mapped[float] = mapped_column(Numeric(10, 2))
    stock_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    accounts: Mapped[list["Account"]] = relationship(back_populates="country")

class Account(Base):
    __tablename__ = 'accounts'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    country_id: Mapped[int] = mapped_column(ForeignKey('countries.id'))
    phone_number: Mapped[str] = mapped_column(String(30), unique=True)
    session_file: Mapped[bytes] = mapped_column(LargeBinary)
    tdata_path: Mapped[str] = mapped_column(Text, nullable=True)
    is_sold: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    added_date: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    buyer_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'), nullable=True)
    sold_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)
    country: Mapped["Country"] = relationship(back_populates="accounts")
    buyer: Mapped["User"] = relationship()

class Deposit(Base):
    __tablename__ = 'deposits'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    payment_method: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default='pending', index=True)
    screenshot_file_id: Mapped[str] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    admin_channel_message_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    invoice_id: Mapped[int] = mapped_column(BigInteger, nullable=True, index=True)
    user: Mapped["User"] = relationship()

# --- NEW DATABASE TABLE ---
class Withdrawal(Base):
    __tablename__ = 'withdrawals'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    address: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='pending', index=True) # e.g., pending, completed, rejected
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    user: Mapped["User"] = relationship()