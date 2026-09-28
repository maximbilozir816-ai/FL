from __future__ import annotations

import logging
from sqlalchemy import text

from database.engine import async_session_factory

logger = logging.getLogger(__name__)


async def ensure_mini_analysis_column() -> None:
    async with async_session_factory() as session:
        try:
            await session.execute(
                text("ALTER TABLE users ADD COLUMN free_mini_analysis_count INTEGER DEFAULT 1 NOT NULL;")
            )
            await session.commit()
            logger.info("[INFO] Migration: Added 'free_mini_analysis_count' column to 'users' table.")
        except Exception as e:
            await session.rollback()
            logger.debug(f"[DEBUG] Migration ensure_mini_analysis_column skipped: {e}")


async def ensure_mini_stats_columns() -> None:
    async with async_session_factory() as session:
        columns = [
            ("mini_completed", "INTEGER DEFAULT 0"),
            ("mini_passed_qg", "INTEGER DEFAULT 0"),
            ("mini_skipped_qg", "INTEGER DEFAULT 0"),
        ]
        for col_name, col_type in columns:
            try:
                await session.execute(
                    text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};")
                )
                await session.commit()
                logger.info(f"[INFO] Migration: Added '{col_name}' column to 'users' table.")
            except Exception as e:
                await session.rollback()
                logger.debug(f"[DEBUG] Migration ensure_mini_stats_columns ({col_name}) skipped: {e}")


async def ensure_payment_charge_id_unique() -> None:
    async with async_session_factory() as session:
        try:
            await session.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_telegram_payment_charge_id ON payments (telegram_payment_charge_id);")
            )
            await session.commit()
            logger.info("[INFO] Migration: Ensured unique index on payments.telegram_payment_charge_id.")
        except Exception as e:
            await session.rollback()
            logger.debug(f"[DEBUG] Migration ensure_payment_charge_id_unique skipped: {e}")


async def ensure_discount_columns() -> None:
    """Ідемпотентна міграція: додає колонки знижки в таблицю users, якщо їх ще немає."""
    async with async_session_factory() as session:
        columns = [
            ("discount_offered_at", "TIMESTAMP WITH TIME ZONE"),
            ("discount_expires_at", "TIMESTAMP WITH TIME ZONE"),
            ("discount_used", "BOOLEAN DEFAULT FALSE"),
            ("discount_expiry_notified", "BOOLEAN DEFAULT FALSE"),
            ("discount_10m_notified", "BOOLEAN DEFAULT FALSE"),
        ]
        for col_name, col_type in columns:
            try:
                # Використовуємо окрему транзакцію для кожної колонки у SQLite, 
                # оскільки помилка ALTER TABLE викидає exception і ламає загальну сесію
                async with session.begin_nested():
                    await session.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};"))
                await session.commit()
                logger.info(f"[INFO] Migration: Added '{col_name}' column.")
            except Exception as e:
                logger.debug(f"[DEBUG] Migration ensure_discount_columns ({col_name}) skipped: {e}")