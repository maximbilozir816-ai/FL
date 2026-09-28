# handlers/photo.py
from __future__ import annotations

import io
import logging

from face.utils.mesh_drawer import generate_mesh_photo_b64

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import settings
from database.repository import StatsRepository, UserRepository
from face.utils import get_pdf_executor, get_temp_manager, get_user_concurrency_manager
from keyboards.inline import buy_more_keyboard
from services.photo_processor import PhotoRejected, decode_image, process_photo
from services.report_builder import (
    build_metrics_bundle,
    build_overview_contexts,
    build_pdf_bytes,
    request_ai_summaries,
)
from texts import en

# --- НОВИЙ ІМПОРТ ДЛЯ ФУНКЦІЇ БЕЗ ШІ ---
from face.ai_analyzer import _build_fallback_dict

logger = logging.getLogger(__name__)
router = Router(name="photo")


@router.message(lambda m: m.photo)
async def photo_handler(message: Message, bot: Bot, state: FSMContext) -> None:
    chat_id = message.chat.id
    media_group_id = message.media_group_id

    user_data = await state.get_data()
    skip_check = user_data.get("skip_check", False)
    rejection_count = user_data.get("rejection_count", 0)
    
    # Отримуємо стейт вимкненого ШІ для адміна та кастомні оцінки
    admin_ai_disabled = user_data.get("admin_ai_disabled", False)
    admin_force_f = user_data.get("admin_force_f")
    admin_force_d = user_data.get("admin_force_d")

    concurrency_mgr = get_user_concurrency_manager()

    if media_group_id and not settings.process_batch_photos:
        if await concurrency_mgr.is_media_group_duplicate(chat_id, media_group_id):
            return

    async with await concurrency_mgr.acquire_user_lock(chat_id, wait_in_queue=settings.process_batch_photos) as lock_acquired:
        if not lock_acquired:
            await message.answer(en.BUSY_PROCESSING)
            return

        temp_manager = get_temp_manager()
        temp_manager.get_or_create(chat_id)

        balance_deducted = False
        status_msg = None

        try:
            balance = await UserRepository.get_balance(chat_id)
            if balance <= 0:
                is_active, mins, secs = await UserRepository.get_discount_status(chat_id)
                if is_active:
                    btn_text = f"🧠 Get 1 Full Analysis ($2.89) - {mins}m {secs}s"
                else:
                    btn_text = "🧠 Get 1 Full Analysis ($4.29)"
                    
                await message.answer(en.NEED_BALANCE, reply_markup=buy_more_keyboard(btn_1_text=btn_text))
                return

            status_msg = await message.answer(en.STATUS_STEPS[0])

            photo = message.photo[-1]
            buf = io.BytesIO()
            
            # Збільшуємо таймаут до 120 секунд для повільного інтернету або великих файлів
            file_info = await bot.get_file(photo.file_id, request_timeout=120)
            await bot.download_file(file_info.file_path, destination=buf, timeout=120)

            img_orig = decode_image(buf.getvalue(), photo.file_size)
            processed = process_photo(img_orig, chat_id, skip_quality_check=skip_check)

            # --- УСПІШНЕ ПРОХОДЖЕННЯ ---
            if skip_check or rejection_count > 0:
                skip_msg_id = user_data.get("skip_msg_id")
                if skip_msg_id:
                    try:
                        await bot.delete_message(chat_id, skip_msg_id)
                    except Exception as ex:
                        logger.debug(f"Could not delete skip message: {ex}")
                
                # Скидаємо стейт skip_check
                await state.update_data(skip_check=False, rejection_count=0, skip_msg_id=None)

            balance_deducted = await UserRepository.try_deduct_one(chat_id)
            if not balance_deducted:
                is_active, mins, secs = await UserRepository.get_discount_status(chat_id)
                if is_active:
                    btn_text = f"🔥 Get 1 Full Analysis ($2.89) - {mins}m {secs}s"
                else:
                    btn_text = "🧠 Get 1 Full Analysis ($4.29)"
                    
                await status_msg.edit_text(en.NEED_BALANCE, reply_markup=buy_more_keyboard(btn_1_text=btn_text))
                return

            await status_msg.edit_text(en.STATUS_STEPS[1])
            bundle = build_metrics_bundle(
                processed.metrics, processed.image_crop_bgr, processed.landmarks,
                processed.width_crop, processed.height_crop,
            )

            await status_msg.edit_text(en.STATUS_STEPS[2])
            
            # --- ЛОГІКА ДЛЯ АДМІНА (Вимикаємо дорогий запит OpenAI, якщо увімкнено /aioff) ---
            if admin_ai_disabled:
                logger.info(f"[INFO] Admin AI disabled - using fallback texts for {chat_id}")
                ai_texts = _build_fallback_dict()
            else:
                ai_texts = await request_ai_summaries(bundle, chat_id)
            # -------------------------------------------------------------------------------------

            # ПЕРЕДАЄМО КАСТОМНІ ОЦІНКИ ОДРАЗУ В ГЕНЕРАТОР, щоб відсотки та рівні розрахувалися правильно
            contexts = build_overview_contexts(
                bundle, 
                ai_texts,
                force_f=admin_force_f,
                force_d=admin_force_d
            )

            # --- ЛОГІКА ДЛЯ СІТКИ ТА ОЧИЩЕННЯ АДМІНСЬКИХ ОЦІНОК ---
            mesh_photo_src = generate_mesh_photo_b64(
                img_numpy=processed.image_crop_bgr,
                landmarks=processed.landmarks,
                width=processed.width_crop,
                height=processed.height_crop
            )
            
            if "overall_score_ctx" in contexts and contexts["overall_score_ctx"]:
                contexts["overall_score_ctx"].photo_src = mesh_photo_src
                
                # Якщо ми використали кастомні оцінки - очищаємо їх зі стану, щоб наступне фото було чесним
                if admin_force_f is not None or admin_force_d is not None:
                    await state.update_data(admin_force_f=None, admin_force_d=None)
                    logger.info(f"Applied forced admin scores for {chat_id} and cleared state.")
            # ----------------------------------------------

            await status_msg.edit_text(en.STATUS_STEPS[3])
            pdf_bytes = await build_pdf_bytes(bundle, contexts, chat_id)

            await status_msg.edit_text(en.STATUS_STEPS[4])

            await UserRepository.increment_completed_analyses(chat_id)
            today_count = await StatsRepository.increment_today_count()

            quality_line = en.QUALITY_LINE_OFF if skip_check else (en.QUALITY_LINE_ON if settings.quality_gate_enabled else en.QUALITY_LINE_OFF)
            
            caption = en.REPORT_CAPTION.format(
                actor_name=ai_texts.get("best_actor_match", "Not identified"),
                actor_advice=ai_texts.get("actor_style_advice", "Follow classic proportions."),
                study_links=ai_texts.get("scientific_links", ""),
                quality_line=quality_line
            )

            try:
                await status_msg.delete()
            except Exception:
                pass

            await message.reply_document(
                document=BufferedInputFile(pdf_bytes, filename="face_analysis.pdf"),
                caption=caption,
                parse_mode="HTML",
                request_timeout=300,
            )

            await UserRepository.trigger_discount_if_eligible(chat_id)
            
            logger.info(f"[INFO] ✅ ANALYSIS ISSUED | ID: {chat_id} | Today total: {today_count}")

        except PhotoRejected as e:
            logger.warning(f"[ERROR] ⚠️ PHOTO REJECTED | ID: {chat_id} | Reason: {e.message[:50]}...")
            if balance_deducted:
                await UserRepository.refund_one(chat_id)
            
            is_qg_error = getattr(e, 'is_quality_gate', False)
            
            if is_qg_error:
                rejection_count += 1
                await state.update_data(rejection_count=rejection_count)
                rejection_text = f"{en.QUALITY_GATE_REJECTED_HEADER}{e.message}\n\n{en.QUALITY_GATE_TIP}"
            else:
                rejection_text = e.message

            if status_msg:
                await status_msg.edit_text(rejection_text, parse_mode="HTML")
            else:
                await message.answer(rejection_text, parse_mode="HTML")
                
            if is_qg_error and rejection_count >= 3:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=en.BTN_SKIP_CHECK, callback_data="skip_quality_check")]
                ])
                skip_msg = await message.answer(en.SKIP_QUALITY_CHECK_MSG, reply_markup=kb, parse_mode="HTML")
                await state.update_data(skip_msg_id=skip_msg.message_id)

        except Exception as e:
            logger.error(f"[ERROR] User {chat_id} failed processing: {e}", exc_info=True)
            if balance_deducted:
                await UserRepository.refund_one(chat_id)
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