# database/engine.py
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from database.models import Base

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url, echo=False, future=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

if settings.database_url.startswith("sqlite"):
    # NOTE (production readiness): SQLite serializes writes at the file
    # level. Once payment webhooks (writing Payment/User rows) and normal
    # bot traffic (writing balance deductions on every photo) happen
    # concurrently in production, this becomes a real source of
    # "database is locked" errors / write contention. Fine for local dev
    # and small-scale testing; switch DATABASE_URL to Postgres before
    # relying on this for real payment volume.
    logger.warning(
        "[WARN] Using SQLite (%s). This is fine for development, but is not "
        "recommended for production once concurrent webhook + bot writes "
        "are expected -- consider switching DATABASE_URL to Postgres.",
        settings.database_url,
    )


async def init_db() -> None:
    """Create all tables if they don't exist yet. Call once on bot startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized.")