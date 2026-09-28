"""
All DB access goes through this repository. No handler or service should
import SQLAlchemy models directly -- this keeps persistence swappable and
testable.
"""

from __future__ import annotations

import datetime as dt
import logging
import random
from typing import Optional

from sqlalchemy import select, update, func, delete, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import async_session_factory
from database.models import DailyStat, Payment, User

logger = logging.getLogger(__name__)


class UserRepository:

    @staticmethod
    async def get_or_create(telegram_id: int, username: Optional[str] = None, source: Optional[str] = None) -> User:
        async with async_session_factory() as session:
            user = await UserRepository._get(session, telegram_id)
            if user:
                if username and user.username != username:
                    user.username = username
                    await session.commit()
                return user

            user = User(telegram_id=telegram_id, username=username, balance=0, source=source)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"[INFO] User {telegram_id} registered. Source: {source}")
            return user
        
    @staticmethod
    async def get_all_user_ids() -> list[int]:
        async with async_session_factory() as session:
            result = await session.execute(select(User.telegram_id))
            return list(result.scalars().all())

    @staticmethod
    async def _get(session: AsyncSession, telegram_id: int) -> Optional[User]:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_balance(telegram_id: int) -> int:
        async with async_session_factory() as session:
            user = await UserRepository._get(session, telegram_id)
            return user.balance if user else 0

    @staticmethod
    async def add_balance(telegram_id: int, amount: int) -> int:
        async with async_session_factory() as session:
            user = await UserRepository._get(session, telegram_id)
            if not user:
                user = User(telegram_id=telegram_id, balance=0)
                session.add(user)
                await session.flush()

            user.balance = max(0, user.balance + amount)
            if amount > 0:
                user.total_purchased += amount
            await session.commit()
            await session.refresh(user)
            logger.info(f"[INFO] User {telegram_id} balance credited {amount:+d} (new balance: {user.balance}).")
            return user.balance

    @staticmethod
    async def get_user_info(telegram_id: int) -> Optional[User]:
        async with async_session_factory() as session:
            return await UserRepository._get(session, telegram_id)

    @staticmethod
    async def subtract_balance(telegram_id: int, amount: int) -> Optional[int]:
        async with async_session_factory() as session:
            user = await UserRepository._get(session, telegram_id)
            if not user:
                return None

            user.balance = max(0, user.balance - amount)
            await session.commit()
            await session.refresh(user)
            logger.info(f"[INFO] User {telegram_id} balance debited -{amount} by admin (new balance: {user.balance}).")
            return user.balance

    @staticmethod
    async def try_deduct_one(telegram_id: int) -> bool:
        async with async_session_factory() as session:
            result = await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id, User.balance > 0)
                .values(balance=User.balance - 1)
            )
            await session.commit()
            success = result.rowcount > 0
            if success:
                logger.info(f"[INFO] User {telegram_id} balance deducted (1 analysis).")
            return success

    @staticmethod
    async def refund_one(telegram_id: int) -> None:
        await UserRepository.add_balance(telegram_id, 1)
        logger.info(f"[INFO] User {telegram_id} refunded 1 analysis after failure.")

    @staticmethod
    async def increment_completed_analyses(telegram_id: int) -> None:
        async with async_session_factory() as session:
            user = await UserRepository._get(session, telegram_id)
            if user:
                user.total_analyses_done += 1
                await session.commit()

    @staticmethod
    async def purchase_already_processed(purchase_id: Optional[str | int]) -> bool:
        if purchase_id is None:
            return False
        async with async_session_factory() as session:
            result = await session.execute(
                select(Payment).where(Payment.telegram_payment_charge_id == str(purchase_id))
            )
            return result.scalar_one_or_none() is not None

    @staticmethod
    async def record_payment(
        telegram_id: int,
        amount: int,
        currency: str,
        telegram_payment_charge_id: Optional[str] = None,
        provider_payment_charge_id: Optional[str] = None,
    ) -> None:
        async with async_session_factory() as session:
            session.add(
                Payment(
                    telegram_id=telegram_id,
                    amount=amount,
                    currency=currency,
                    telegram_payment_charge_id=telegram_payment_charge_id,
                    provider_payment_charge_id=provider_payment_charge_id,
                )
            )
            await session.commit()

    @staticmethod
    async def credit_payment(
        telegram_id: int,
        credit_amount: int,
        amount_cents: Optional[int],
        currency: Optional[str],
        payment_ref: str,
        provider_ref: Optional[str] = None,
        mark_discount_used: bool = False,
    ) -> Optional[int]:
        async with async_session_factory() as session:
            try:
                session.add(
                    Payment(
                        telegram_id=telegram_id,
                        amount=amount_cents,
                        currency=currency,
                        telegram_payment_charge_id=payment_ref,
                        provider_payment_charge_id=provider_ref,
                    )
                )
                await session.flush()

                user = await UserRepository._get(session, telegram_id)
                if not user:
                    user = User(telegram_id=telegram_id, balance=0)
                    session.add(user)
                    await session.flush()

                user.balance = max(0, user.balance + credit_amount)
                if credit_amount > 0:
                    user.total_purchased += credit_amount

                if mark_discount_used:
                    user.discount_used = True

                await session.commit()
                await session.refresh(user)
                logger.info(
                    f"[INFO] Payment '{payment_ref}' credited to user {telegram_id}: "
                    f"{credit_amount:+d} (new balance: {user.balance})."
                )
                return user.balance

            except IntegrityError:
                await session.rollback()
                logger.info(
                    f"[INFO] Payment '{payment_ref}' already processed (unique constraint hit), skipping."
                )
                return None

    # --- DISCOUNT METHODS ---

    @staticmethod
    async def admin_zero_discount(telegram_id: int) -> str:
        async with async_session_factory() as session:
            user = await UserRepository._get(session, telegram_id)
            if not user:
                return "User not found in DB."
            
            if not user.discount_offered_at:
                return "User didn't use free analysis yet and didn't have discount."
            
            now = dt.datetime.now(dt.timezone.utc)
            expires_at = user.discount_expires_at
            if expires_at and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=dt.timezone.utc)
                
            if expires_at and now >= expires_at:
                return "User's discount already timed up."
                
            user.discount_expires_at = now
            await session.commit()
            return f"✅ Discount for user <code>{telegram_id}</code> has been successfully zeroed out."

    @staticmethod
    async def admin_add_discount(telegram_id: int) -> str:
        async with async_session_factory() as session:
            user = await UserRepository._get(session, telegram_id)
            if not user:
                return "User not found in DB."
            
            now = dt.datetime.now(dt.timezone.utc)
            expires_at = user.discount_expires_at
            if expires_at and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=dt.timezone.utc)
                
            is_active = False
            if user.discount_offered_at and expires_at and now < expires_at:
                is_active = True
                
            user.discount_offered_at = now
            user.discount_expires_at = now + dt.timedelta(minutes=20)
            user.discount_used = False
            user.discount_expiry_notified = False
            user.discount_10m_notified = False
            
            await session.commit()
            
            if is_active:
                return f"✅ User <code>{telegram_id}</code> already had an active discount. Timer reset to fresh 20 minutes."
            else:
                return f"✅ Fresh 20-minute discount added to user <code>{telegram_id}</code>."

    @staticmethod
    async def trigger_discount_if_eligible(telegram_id: int) -> None:
        """Triggers the discount. Sets visual timer to 20 mins."""
        async with async_session_factory() as session:
            user = await UserRepository._get(session, telegram_id)
            if user:
                now = dt.datetime.now(dt.timezone.utc)
                user.discount_offered_at = now
                user.discount_expires_at = now + dt.timedelta(minutes=20)
                user.discount_used = False
                await session.commit()
                logger.info(f"[INFO] 20-min visual discount triggered for user {telegram_id}.")

    @staticmethod
    async def get_discount_status(telegram_id: int) -> tuple[bool, int, int]:
        """Returns (is_active, minutes, seconds) based strictly on 20m timer."""
        async with async_session_factory() as session:
            user = await UserRepository._get(session, telegram_id)
            if not user or not user.discount_expires_at:
                return False, 0, 0
            
            now = dt.datetime.now(dt.timezone.utc)
            expires_at = user.discount_expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=dt.timezone.utc)

            if now < expires_at:
                total_seconds = int((expires_at - now).total_seconds())
                mins, secs = divmod(total_seconds, 60)
                return True, mins, secs
                
            return False, 0, 0

    @staticmethod
    async def check_discount_grace_period(telegram_id: int) -> bool:
        """SECRET GRACE PERIOD: 20 visual mins + 2 buffer mins = 22 mins total for payments."""
        async with async_session_factory() as session:
            user = await UserRepository._get(session, telegram_id)
            if not user or not user.discount_expires_at:
                return False
            
            now = dt.datetime.now(dt.timezone.utc)
            expires_at = user.discount_expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=dt.timezone.utc)
                
            return now < (expires_at + dt.timedelta(minutes=2))

    @staticmethod
    async def get_expired_unnotified_discounts() -> list[int]:
        """Finds users whose discount just expired and need a notification."""
        async with async_session_factory() as session:
            now = dt.datetime.now(dt.timezone.utc)
            result = await session.execute(
                select(User.telegram_id)
                .where(
                    User.discount_expires_at < now,
                    User.discount_used == False,
                    User.discount_expiry_notified == False
                )
            )
            return list(result.scalars().all())

    @staticmethod
    async def mark_discount_notified(telegram_id: int) -> None:
        async with async_session_factory() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(discount_expiry_notified=True)
            )
            await session.commit()

    @staticmethod
    async def get_users_for_10m_warning() -> list[int]:
        """Finds users with <= 10 visual minutes left."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(User)
                .where(
                    User.discount_expires_at.is_not(None),
                    User.discount_used == False,
                    User.discount_10m_notified == False
                )
            )
            users = result.scalars().all()
            
            warn_list = []
            now = dt.datetime.now(dt.timezone.utc)
            for user in users:
                expires_at = user.discount_expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=dt.timezone.utc)
                
                if now < expires_at:
                    seconds_left = (expires_at - now).total_seconds()
                    if seconds_left <= 600:
                        warn_list.append(user.telegram_id)
                        
            return warn_list

    @staticmethod
    async def mark_discount_10m_notified(telegram_id: int) -> None:
        async with async_session_factory() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(discount_10m_notified=True)
            )
            await session.commit()

    # --- ADMIN STATS METHODS ---
    @staticmethod
    async def get_total_users_count() -> int:
        async with async_session_factory() as session:
            result = await session.execute(select(func.count(User.telegram_id)))
            return result.scalar() or 0

    @staticmethod
    async def get_payment_stats() -> dict:
        PACKAGE_SPLIT_CENTS = 650

        async with async_session_factory() as session:
            result = await session.execute(select(Payment))
            payments = result.scalars().all()

            stats = {
                "tribute_1": 0,
                "donation_1": 0,
                "tribute_3": 0,
                "donation_3": 0
            }

            for p in payments:
                if not p.amount:
                    continue

                is_donation = p.telegram_payment_charge_id and p.telegram_payment_charge_id.startswith("donation:")

                if p.amount <= PACKAGE_SPLIT_CENTS:
                    stats["donation_1" if is_donation else "tribute_1"] += 1
                else:
                    stats["donation_3" if is_donation else "tribute_3"] += 1

            return stats
            
    @staticmethod
    async def get_traffic_stats() -> dict[str, int]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(User.source, func.count(User.telegram_id)).group_by(User.source)
            )
            stats = {}
            for row in result.all():
                source = row[0] or "organic (no link)"
                count = row[1]
                stats[source] = count
            return stats

    @staticmethod
    async def clear_all_stats() -> None:
        async with async_session_factory() as session:
            await session.execute(delete(Payment))
            await session.execute(delete(DailyStat))
            await session.commit()
            logger.info("[INFO] Admin cleared all payment and daily statistics from the database.")


class StatsRepository:
    @staticmethod
    def _today() -> str:
        return dt.date.today().isoformat()

    @staticmethod
    async def get_today_count() -> int:
        async with async_session_factory() as session:
            today = StatsRepository._today()
            result = await session.execute(select(DailyStat).where(DailyStat.date == today))
            row = result.scalar_one_or_none()
            
            # If no record exists for today (new day started), initialize with a random value (50-90)
            if row is None:
                random_initial = random.randint(50, 90)
                row = DailyStat(date=today, analyses_count=random_initial)
                session.add(row)
                await session.commit()
                logger.info(f"[INFO] Initialized today's counter with random value: {random_initial}")
                return random_initial

            return row.analyses_count

    @staticmethod
    async def set_random_today_count(min_val: int = 50, max_val: int = 90) -> int:
        """Forces setting a new random value for today's counter."""
        async with async_session_factory() as session:
            today = StatsRepository._today()
            result = await session.execute(select(DailyStat).where(DailyStat.date == today))
            row = result.scalar_one_or_none()

            random_val = random.randint(min_val, max_val)

            if row is None:
                row = DailyStat(date=today, analyses_count=random_val)
                session.add(row)
            else:
                row.analyses_count = random_val

            await session.commit()
            logger.info(f"[INFO] Admin manually set today's counter to: {random_val}")
            return random_val

    @staticmethod
    async def increment_today_count() -> int:
        async with async_session_factory() as session:
            today = StatsRepository._today()
            result = await session.execute(select(DailyStat).where(DailyStat.date == today))
            row = result.scalar_one_or_none()
            if row is None:
                random_initial = random.randint(50, 90)
                row = DailyStat(date=today, analyses_count=random_initial)
                session.add(row)
            row.analyses_count += 1
            await session.commit()
            return row.analyses_count

    @staticmethod
    async def add_to_today_count(amount: int) -> int:
        async with async_session_factory() as session:
            today = StatsRepository._today()
            result = await session.execute(select(DailyStat).where(DailyStat.date == today))
            row = result.scalar_one_or_none()
            if row is None:
                random_initial = random.randint(50, 90)
                row = DailyStat(date=today, analyses_count=random_initial)
                session.add(row)

            row.analyses_count += amount
            await session.commit()
            return row.analyses_count

    @staticmethod
    async def reset_today_count() -> None:
        async with async_session_factory() as session:
            await session.execute(delete(DailyStat))
            await session.commit()
            logger.info("[INFO] Daily statistics have been reset by admin.")