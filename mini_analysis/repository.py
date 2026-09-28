"""
Isolated repository for the free mini-analysis counter
(`User.free_mini_analysis_count`).

Deliberately does NOT import or extend `database.repository.UserRepository`
so the payment/balance code path is never touched by this feature. Uses the
same async session factory and the same atomic-conditional-UPDATE pattern
as `UserRepository.try_deduct_one` to avoid double-spending free tries under
concurrent requests.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select, update

from database.engine import async_session_factory
from database.models import User

from sqlalchemy import select, func
from database.models import User
from database.engine import async_session_factory

logger = logging.getLogger(__name__)


class MiniAnalysisRepository:

    @staticmethod
    async def get_free_balance(telegram_id: int) -> int:
        async with async_session_factory() as session:
            result = await session.execute(
                select(User.free_mini_analysis_count).where(User.telegram_id == telegram_id)
            )
            value = result.scalar_one_or_none()
            return value or 0

    @staticmethod
    async def try_deduct_one_free(telegram_id: int) -> bool:
        """Atomically deducts 1 free try IF the count > 0. Same double-spend
        protection as UserRepository.try_deduct_one, scoped to the free counter."""
        async with async_session_factory() as session:
            result = await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id, User.free_mini_analysis_count > 0)
                .values(free_mini_analysis_count=User.free_mini_analysis_count - 1)
            )
            await session.commit()
            success = result.rowcount > 0
            if success:
                logger.info(f"[INFO] User {telegram_id} free mini-analysis try consumed.")
            return success

    @staticmethod
    async def refund_one_free(telegram_id: int) -> None:
        """Used when a free analysis fails after the try was already deducted."""
        async with async_session_factory() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(free_mini_analysis_count=User.free_mini_analysis_count + 1)
            )
            await session.commit()
            logger.info(f"[INFO] User {telegram_id} refunded 1 free mini-analysis try after failure.")

    @staticmethod
    async def add_free_tries(telegram_id: int, amount: int) -> Optional[int]:
        """Admin grant. Returns the new total, or None if the user doesn't exist."""
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()
            if not user:
                return None

            user.free_mini_analysis_count += amount
            await session.commit()
            await session.refresh(user)
            logger.info(
                f"[INFO] User {telegram_id} granted {amount:+d} free mini-analysis tries "
                f"(new total: {user.free_mini_analysis_count})."
            )
            return user.free_mini_analysis_count
        
    @staticmethod
    async def record_mini_completion(telegram_id: int, skipped: bool) -> None:
        """Записує факт проходження міні-аналізу та статус quality gate."""
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()
            if user:
                user.mini_completed += 1
                if skipped:
                    user.mini_skipped_qg += 1
                else:
                    user.mini_passed_qg += 1
                await session.commit()

    @staticmethod
    async def get_mini_stats() -> dict:
        """Повертає статистику по міні-аналізам для команди /stats."""
        async with async_session_factory() as session:
            completed = (await session.execute(select(func.count(User.id)).where(User.mini_completed > 0))).scalar() or 0
            passed = (await session.execute(select(func.count(User.id)).where(User.mini_passed_qg > 0))).scalar() or 0
            skipped = (await session.execute(select(func.count(User.id)).where(User.mini_skipped_qg > 0))).scalar() or 0

            return {
                "completed": completed,
                "passed": passed,
                "skipped": skipped
            }
