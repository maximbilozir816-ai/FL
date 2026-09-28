from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, DateTime, Integer, String, func, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_analyses_done: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_purchased: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # --- НОВЕ ПОЛЕ ДЛЯ СТАТИСТИКИ (Джерело трафіку) ---
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # ----------------------------------------------------

    # --- NEW: free mini-analysis feature -------------------------------
    free_mini_analysis_count: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, server_default="1"
    )

    mini_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    mini_passed_qg: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    mini_skipped_qg: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # ---------------------------------------------------------------------

    # --- NEW: One-time discount feature ----------------------------------
    discount_offered_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discount_expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discount_used: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    discount_expiry_notified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    discount_10m_notified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # ---------------------------------------------------------------------

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    telegram_payment_charge_id: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=True
    )
    provider_payment_charge_id: Mapped[str] = mapped_column(String(128), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DailyStat(Base):
    __tablename__ = "daily_stats"

    date: Mapped[str] = mapped_column(String(10), primary_key=True)
    analyses_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)