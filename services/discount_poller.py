import asyncio
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.repository import UserRepository
from config import settings
from texts import en
from keyboards.inline import CB_GET_ANALYSIS

logger = logging.getLogger(__name__)

async def start_discount_poller(bot: Bot):
    logger.info("[INFO] Starting discount expiration poller...")
    
    # Кнопка для швидкого переходу до оплати з нагадування
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Get Full Face Analysis", callback_data=CB_GET_ANALYSIS)]
    ])

    while True:
        try:
            # 1. Перевірка на 10 хвилин
            users_to_warn = await UserRepository.get_users_for_10m_warning()
            for telegram_id in users_to_warn:
                try:
                    await bot.send_message(
                        chat_id=telegram_id, 
                        text=en.DISCOUNT_10M_WARNING, 
                        parse_mode="HTML",
                        reply_markup=markup
                    )
                except Exception as e:
                    logger.error(f"[ERROR] Failed to warn user {telegram_id} about 10m: {e}")
                finally:
                    await UserRepository.mark_discount_10m_notified(telegram_id)

            # 2. Перевірка на закінчення часу
            # 2. Перевірка на закінчення часу
            users_to_expire = await UserRepository.get_expired_unnotified_discounts()
            for telegram_id in users_to_expire:
                try:
                    # Важливо: форматуємо повідомлення, передаючи лінк на підтримку
                    text = en.DISCOUNT_EXPIRED_MSG.format(support="@mbilozir22")
                    await bot.send_message(chat_id=telegram_id, text=text, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"[ERROR] Failed to notify user {telegram_id} about expiration: {e}")
                finally:
                    await UserRepository.mark_discount_notified(telegram_id)
                    
        except Exception as e:
            logger.error(f"[ERROR] Poller error: {e}")
            
        # Перевіряємо кожні 30 секунд для більшої точності
        await asyncio.sleep(30)