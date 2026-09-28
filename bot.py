# bot.py
from __future__ import annotations

import os
import sys

if sys.platform == "win32":
    os.add_dll_directory(r"C:\msys64\ucrt64\bin")
    
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from database.engine import init_db
from handlers import callbacks, photo, start
import webhooks

from database.migrations import (
    ensure_mini_analysis_column,
    ensure_mini_stats_columns,
    ensure_payment_charge_id_unique,  # NEW: bugfix migration, see migrations.py
)
from mini_analysis.handlers import router as mini_analysis_router
from mini_analysis.admin import router as mini_analysis_admin_router

from database.migrations import (
    ensure_mini_analysis_column,
    ensure_mini_stats_columns,
    ensure_payment_charge_id_unique,
    ensure_discount_columns,  # ДОДАНО: міграція для знижок
)

from services.discount_poller import start_discount_poller  # ДОДАНО: імпорт поллера

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    os.add_dll_directory(r"C:\msys64\ucrt64\bin")

# Initialize bot and dispatcher globally so they can be accessed
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
    # Silence chatty libraries completely
    logging.getLogger("weasyprint").setLevel(logging.ERROR)
    logging.getLogger("fontTools").setLevel(logging.ERROR)
    for noisy_logger in ("aiogram.event", "httpx", "openai"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI. 
    Handles startup and shutdown events for the bot.
    """
    configure_logging()
    logger.info("[INFO] Application starting...")

    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Add it to your .env file.")

    await init_db()
    await ensure_mini_analysis_column()
    await ensure_mini_stats_columns()
    await ensure_payment_charge_id_unique()
    await ensure_discount_columns() # ДОДАНО: створюємо колонки для знижки, якщо їх немає

    # Pass the bot instance to the webhooks router
    webhooks.bot = bot

    # Include bot routers
    dp.include_router(start.router)
    dp.include_router(callbacks.router)
    dp.include_router(mini_analysis_router)
    dp.include_router(mini_analysis_admin_router)
    dp.include_router(photo.router)

    await bot.delete_webhook(drop_pending_updates=True)

    # Start bot polling in a background task
    polling_task = asyncio.create_task(dp.start_polling(bot))
    
    # ДОДАНО: Запуск фонового процесу перевірки знижок
    poller_task = asyncio.create_task(start_discount_poller(bot))
    
    logger.info("[INFO] Bot started (polling mode).")

    yield  # Here the FastAPI server runs and listens for incoming requests (like Webhooks)

    # Shutdown sequence
    logger.info("[INFO] Application shutting down...")
    polling_task.cancel()
    poller_task.cancel()  # ДОДАНО: коректно зупиняємо поллер при вимкненні
    await bot.session.close()


# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

# Include the webhooks router
app.include_router(webhooks.router)


if __name__ == "__main__":
    # Run the combined server locally. 
    # Use Ngrok to expose port 8000 to the internet for Tribute webhooks.
    uvicorn.run(app, host="0.0.0.0", port=8000)