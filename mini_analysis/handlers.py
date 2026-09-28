from __future__ import annotations

import io
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.inline import CB_GET_ANALYSIS

from face.utils import get_temp_manager, get_user_concurrency_manager
from keyboards.inline import buy_more_keyboard
from services.photo_processor import PhotoRejected, decode_image, process_photo
from texts import en

from aiogram.filters import Command
from database.repository import StatsRepository, UserRepository
from keyboards.inline import start_keyboard

from mini_analysis import texts as mtexts
from mini_analysis.constants import (
    CB_GET_MINI_ANALYSIS,
    STATE_KEY_AWAITING_MINI_PHOTO,
    STATE_KEY_MINI_INSTRUCTION_MSG_ID,
)
from mini_analysis.document_builder import build_mini_pdf_bytes
from mini_analysis.filters import AwaitingMiniPhoto
from mini_analysis.pipeline import build_mini_metric_pages
from mini_analysis.repository import MiniAnalysisRepository

logger = logging.getLogger(__name__)
router = Router(name="mini_analysis")


@router.callback_query(F.data == CB_GET_MINI_ANALYSIS)
async def start_mini_analysis(callback: CallbackQuery, state: FSMContext) -> None:
    telegram_id = callback.from_user.id
    balance = await MiniAnalysisRepository.get_free_balance(telegram_id)
    if balance <= 0:
        await callback.answer(mtexts.NO_FREE_TRIES_LEFT, show_alert=True)
        return

    await state.update_data(
        **{
            STATE_KEY_AWAITING_MINI_PHOTO: True,
        }
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Get free analysis later", callback_data="mini_later")]
    ])
    
    msg = await callback.message.answer(mtexts.MINI_PHOTO_INSTRUCTIONS, parse_mode="HTML", reply_markup=markup)
    await state.update_data(**{STATE_KEY_MINI_INSTRUCTION_MSG_ID: msg.message_id})
    await callback.answer()


@router.callback_query(F.data == "mini_later")
async def cancel_mini_analysis(callback: CallbackQuery, state: FSMContext) -> None:
    # 1. Знімаємо стан очікування фото
    await state.update_data(**{STATE_KEY_AWAITING_MINI_PHOTO: False})
    
    # 2. Просто видаляємо повідомлення з інструкцією та кнопкою "Get free analysis later"
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    await callback.answer()


@router.message(Command("minus_minitries"))
async def minus_mini_tries_cmd(message: Message) -> None:
    """Команда для віднімання 1 міні-спроби (для тестів/адміністрування)"""
    chat_id = message.chat.id
    success = await MiniAnalysisRepository.try_deduct_one_free(chat_id)
    
    if success:
        await message.answer("✅ 1 free mini-analysis try has been successfully deducted.")
    else:
        await message.answer("❌ You don't have any free mini-analysis tries left to deduct.")


@router.message(AwaitingMiniPhoto())
async def mini_photo_handler(message: Message, bot: Bot, state: FSMContext) -> None:
    chat_id = message.chat.id

    user_data = await state.get_data()

    concurrency_mgr = get_user_concurrency_manager()

    async with await concurrency_mgr.acquire_user_lock(chat_id, wait_in_queue=False) as lock_acquired:
        if not lock_acquired:
            await message.answer(en.BUSY_PROCESSING)
            return

        temp_manager = get_temp_manager()
        temp_manager.get_or_create(chat_id)

        credit_deducted = False
        status_msg = None

        try:
            balance = await MiniAnalysisRepository.get_free_balance(chat_id)
            if balance <= 0:
                await state.update_data(**{STATE_KEY_AWAITING_MINI_PHOTO: False})
                await message.answer(mtexts.NO_FREE_TRIES_LEFT)
                return

            status_msg = await message.answer(mtexts.MINI_STATUS_PROCESSING)

            photo = message.photo[-1]
            buf = io.BytesIO()
            await bot.download_file((await bot.get_file(photo.file_id)).file_path, destination=buf)

            img_orig = decode_image(buf.getvalue(), photo.file_size)
            # Примусово ігноруємо перевірку якості фото для безкоштовного аналізу
            processed = process_photo(img_orig, chat_id, skip_quality_check=True)

            credit_deducted = await MiniAnalysisRepository.try_deduct_one_free(chat_id)
            if not credit_deducted:
                await status_msg.edit_text(mtexts.NO_FREE_TRIES_LEFT)
                return

            pages = build_mini_metric_pages(processed)
            pdf_bytes = build_mini_pdf_bytes(processed.image_crop_bgr, pages)

            # Clean up the instruction message now that the analysis succeeded.
            instruction_msg_id = user_data.get(STATE_KEY_MINI_INSTRUCTION_MSG_ID)
            if instruction_msg_id:
                try:
                    await bot.delete_message(chat_id, instruction_msg_id)
                except Exception as ex:
                    logger.debug(f"Could not delete mini instruction message: {ex}")

            try:
                await status_msg.delete()
            except Exception:
                pass

            # Записуємо успішне виконання в базу
            await MiniAnalysisRepository.record_mini_completion(chat_id, skipped=True)

            final_caption = mtexts.MINI_REPORT_CAPTION

            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐️ Get Full Face Analysis", callback_data=CB_GET_ANALYSIS)]
            ])

            await message.reply_document(
                document=BufferedInputFile(pdf_bytes, filename="free_ratio_analysis.pdf"),
                caption=final_caption,
                parse_mode="HTML",
                reply_markup=markup,
                request_timeout=300,
            )

            await UserRepository.trigger_discount_if_eligible(chat_id)

            await state.update_data(
                **{STATE_KEY_AWAITING_MINI_PHOTO: False, STATE_KEY_MINI_INSTRUCTION_MSG_ID: None}
            )
            logger.info(f"[INFO] ✅ FREE MINI-ANALYSIS ISSUED | ID: {chat_id}")

        except PhotoRejected as e:
            logger.warning(f"[WARN] Mini-analysis photo rejected | ID: {chat_id} | Reason: {e.message[:50]}...")
            if credit_deducted:
                await MiniAnalysisRepository.refund_one_free(chat_id)

            if status_msg:
                await status_msg.edit_text(e.message, parse_mode="HTML")
            else:
                await message.answer(e.message, parse_mode="HTML")

        except Exception as e:
            logger.error(f"[ERROR] Mini-analysis failed for user {chat_id}: {e}", exc_info=True)
            if credit_deducted:
                await MiniAnalysisRepository.refund_one_free(chat_id)
            try:
                if status_msg:
                    await status_msg.edit_text(en.GENERIC_ERROR)
                else:
                    await message.answer(en.GENERIC_ERROR)
            except Exception:
                pass

        finally:
            temp_manager.cleanup_user(chat_id)
            await concurrency_mgr.cleanup_user_state(chat_id)