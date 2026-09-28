from __future__ import annotations

import logging
import os

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from config import settings
from database.repository import StatsRepository, UserRepository
from keyboards.inline import (
    CB_BACK_TO_START,
    CB_GET_ANALYSIS,
    CB_GET_FULL_ANALYSIS_1,
    CB_GET_FULL_ANALYSIS_3,
    CB_MANUAL_PAYMENT,
    details_keyboard,
    manual_payment_keyboard,
    payment_keyboard,
    start_keyboard,
    back_only_keyboard,
)
from texts import en

logger = logging.getLogger(__name__)
router = Router(name="callbacks")

from mini_analysis.repository import MiniAnalysisRepository 

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


async def safe_edit_text(callback: CallbackQuery, text: str, **kwargs) -> None:
    try:
        await callback.message.edit_text(text, **kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            logger.debug("Ignored 'message is not modified' for callback %s", callback.data)
        else:
            raise

@router.callback_query(lambda c: c.data == CB_BACK_TO_START)
async def back_to_start(callback: CallbackQuery) -> None:
    user = await UserRepository.get_or_create(callback.from_user.id, callback.from_user.username)
    today_count = await StatsRepository.get_today_count()
    free_mini_balance = await MiniAnalysisRepository.get_free_balance(callback.from_user.id)

    is_active, mins, secs = await UserRepository.get_discount_status(user.telegram_id)
    
    promo_text = ""
    if is_active:
        promo_text = "\n\n" + en.MAIN_MENU_PROMO_ACTIVE.format(mins=mins, secs=secs)
    elif user.discount_offered_at is None and free_mini_balance > 0:
        promo_text = "\n\n" + en.MAIN_MENU_PROMO_BEFORE

    main_text = (
        "📍 <b>Main menu</b>\n\n"
        "☑️ <b>bp_guide AI</b> mathematically evaluates how harmonious your facial features are.\n\n"
        f"<blockquote>Your balance: <b>{user.balance}</b> analyses\n\n"
        f"Today users performed: <b>{today_count}</b> analyses</blockquote>"
        f"{promo_text}\n\n"
        "⬇️ Get your Ascension guide & Honest face score"
    )

    await safe_edit_text(
        callback,
        main_text,
        reply_markup=start_keyboard(show_free_mini=free_mini_balance > 0),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "skip_quality_check")
async def process_skip_check(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = await state.get_data()
    rejection_count = user_data.get("rejection_count", 0)
    
    if rejection_count < 3:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer("ℹ️ This button is no longer active because your photo was already successfully processed.", parse_mode="HTML")
        await callback.answer()
        return

    await state.update_data(skip_check=True)
    
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    await callback.message.answer(en.SKIP_CHECK_CONFIRMED, parse_mode="HTML")
    await callback.answer()


@router.callback_query(lambda c: c.data == CB_GET_ANALYSIS)
async def show_analysis_details(callback: CallbackQuery) -> None:
    telegram_id = callback.from_user.id
    is_active, mins, secs = await UserRepository.get_discount_status(telegram_id)
    
    if is_active:
        pricing_block = en.PRICING_BLOCK_DISCOUNT.format(mins=mins, secs=secs)
        btn_1_text = f"🔥 Get 1 Full Analysis ($2.89) - {mins}m {secs}s"
    else:
        pricing_block = en.PRICING_BLOCK_NORMAL
        btn_1_text = "🧠 Get 1 Full Analysis ($4.29)"
        
    text = en.ANALYSIS_DETAILS.format(pricing_block=pricing_block)
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=btn_1_text, callback_data=CB_GET_FULL_ANALYSIS_1))
    builder.add(InlineKeyboardButton(text=en.BTN_GET_FULL_ANALYSIS_3, callback_data=CB_GET_FULL_ANALYSIS_3))
    builder.add(InlineKeyboardButton(text=en.BTN_BACK, callback_data=CB_BACK_TO_START))
    builder.adjust(1)
    markup = builder.as_markup()

    if callback.message.document or callback.message.photo:
        await callback.message.answer(text, reply_markup=markup, parse_mode="HTML")
    else:
        await safe_edit_text(callback, text, reply_markup=markup, parse_mode="HTML")
        
    await callback.answer()


@router.callback_query(lambda c: c.data == CB_GET_FULL_ANALYSIS_1)
async def show_payment_screen_1(callback: CallbackQuery) -> None:
    telegram_id = callback.from_user.id
    is_active, mins, secs = await UserRepository.get_discount_status(telegram_id)
    
    discount_block = ""
    # Звичайна ціна за замовчуванням
    price = "4.29" 
    
    if is_active:
        discount_block = en.PAYMENT_DISCOUNT_BLOCK.format(mins=mins, secs=secs)
        # Встановлюємо закреслену ціну для верхнього блоку під час акції
        price = "<del>4.29</del> <b>$2.89</b>"
    
    text = en.PAYMENT_SCREEN.format(
        count=1, 
        is_or_es="is", 
        price=price, # ПЕРЕДАЄМО ЗМІНЕНУ ЦІНУ ТУТ
        discount_block=discount_block
    )
    
    await safe_edit_text(
        callback,
        text,
        reply_markup=payment_keyboard(
            tribute_url=settings.tribute_pay_url or None,
            tribute_stars_url=settings.tribute_stars_pay_url or None,
            package_count=1,
            discount_active=is_active,
        ),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == CB_GET_FULL_ANALYSIS_3)
async def show_payment_screen_3(callback: CallbackQuery) -> None:
    text = en.PAYMENT_SCREEN.format(count=3, is_or_es="es", price="8.99", discount_block="")
    await safe_edit_text(
        callback,
        text,
        reply_markup=payment_keyboard(
            tribute_url=settings.tribute_pay_url_3 or None,
            tribute_stars_url=settings.tribute_stars_pay_url_3 or None,
            package_count=3,
        ),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith(f"{CB_MANUAL_PAYMENT}:"))
async def show_manual_payment_screen(callback: CallbackQuery) -> None:
    package_count = callback.data.split(":")[1]
    
    amount = "8.99" if package_count == "3" else "4.29"
    donation_url = settings.tribute_donation_url
    discount_timer_block = ""

    if package_count == "1":
        # Перевіряємо статус акції (активна, хвилини, секунди)
        is_active, mins, secs = await UserRepository.get_discount_status(callback.from_user.id)
        if is_active:
            # Формуємо закреслену ціну для блоку總支付 або самої суми
            amount = "<del>$4.29</del> <b>$2.89</b>"
            donation_url = settings.tribute_donation_url # або ваш тестовий URL
            # Текст таймера під хлібними крихтами
            discount_timer_block = f"🔥 <b>Your unlimited discount is active for {mins}m {secs}s more!</b>\n\n"

    text = en.MANUAL_PAYMENT_SCREEN.format(
        amount=amount, 
        user_id=callback.from_user.id,
        discount_timer_block=discount_timer_block
    )
    
    await safe_edit_text(
        callback,
        text,
        reply_markup=manual_payment_keyboard(
            donation_url=donation_url or None,
            package_count=package_count 
        ),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "get_help")
async def show_help(callback: CallbackQuery) -> None:
    await safe_edit_text(
        callback,
        "📍 Main menu › <b>Support</b>\n\n<blockquote>If you have any questions or payment issues:\n@mbilozir22</blockquote>",
        reply_markup=back_only_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "project_overview")
async def show_project_info(callback: CallbackQuery) -> None:
    text = (
    "📍 Main Menu › <b>About the Project</b>\n\n"
    "✔️ <b>bp_guide AI</b> is an advanced analytical tool that mathematically evaluates facial geometry, structural alignment, and proportional harmony.\n"
    "⚡ <b>Important:</b> Designed exclusively for <b>men aged 14 and older</b>.\n\n"
    "⚜️ <b>The Core Purpose:</b>\n\n"
    "Attractiveness is rooted in objective biometrics and craniofacial architecture.\n"
    "<blockquote>Calibrated on over <b>100 high-profile male actors</b>, <b>bp_guide AI</b> goes beyond a simple score. It reveals exact structural strengths and weaknesses, giving you a comprehensive <b>Action Plan</b> for grooming, styling, and visual self-improvement.</blockquote>\n\n\n"
    "🔬 <b>Advanced Pipeline (94% Accuracy):</b>\n\n"
    "Standard tools fail due to lens distortion and head tilts. Our system solves this:\n"
    "<blockquote>• <b>Quality Check:</b> Screens for lighting defects and head pose angles.\n"
    "• <b>3D Frontalization:</b> Cancels out head tilt and perspective distortion.\n"
    "• <b>TTA:</b> Analyzes mirrored frames to eliminate measurement bias.</blockquote>\n\n\n"
    "📊 <b>Metrics & Percentiles:</b>\n\n"
    "How Our System Rates You\n"
    "<blockquote>• <b>Percentiles:</b> Your score is calculated via mathematical deviation. The closer your parameters are to ideal standards, the higher your score.\n"
    "• <b>Dimorphism:</b> Evaluates masculine traits. A lower score does not mean you are unattractive; it simply indicates that your features are more feminine.</blockquote>\n\n\n"
    "📚 <b>What You Receive:</b>\n\n"
    "You instantly unlock a comprehensive <b>29-page PDF report</b> containing:\n"
    "<blockquote>• <b>Harmony Score & Percentile:</b> Mathematical ranking against our baseline.\n"
    "• <b>Zone Breakdown:</b> In-depth analysis of eyes, nose, jawline, and facial thirds.\n"
    "• <b>Dimorphism & Archetypes:</b> Phenotypic classification and celebrity comparisons.\n"
    "• <b>Grooming Advisory:</b> Actionable recommendations for haircuts, facial hair, and skincare.</blockquote>\n\n\n"
    "🔒 <b>100% Privacy & Security:</b>\n\n"
    "Your data is absolutely anonymous. <b>All photos are automatically and permanently deleted from our servers immediately after the analysis is complete.</b>\n\n"
    "<b>100% data-driven precision. One photo — one complete blueprint for your image.</b>"
)
    
    await safe_edit_text(
        callback,
        text,
        parse_mode="HTML",
        reply_markup=back_only_keyboard()
    )
    await callback.answer()