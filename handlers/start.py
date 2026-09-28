# handlers/start.py
from __future__ import annotations

import logging
import os
import asyncio

from aiogram import Bot, Router
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import FSInputFile, Message
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError

from config import settings
from database.repository import StatsRepository, UserRepository
from keyboards.inline import start_keyboard

# --- NEW: needed only to check free-mini balance for the main menu button ---
from mini_analysis.repository import MiniAnalysisRepository
# -----------------------------------------------------------------------------

from aiogram.fsm.context import FSMContext

from texts import en

logger = logging.getLogger(__name__)
router = Router(name="start")

# Kept as a fallback default inside settings.admin_id (config.py) so both
# /add_tries here and the manual-donation-review notifications in
# webhooks.py always point at the same admin account.
ADMIN_ID = settings.admin_id


@router.message(Command("aioff"))
async def aioff_command(message: Message, state: FSMContext) -> None:
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(admin_ai_disabled=True)
    await message.answer("✅ <b>AI generation disabled</b>", parse_mode="HTML")

@router.message(Command("aion"))
async def aion_command(message: Message, state: FSMContext) -> None:
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(admin_ai_disabled=False)
    await message.answer("✅ <b>AI generation enabled</b>", parse_mode="HTML")

@router.message(Command("reset_random"))
async def reset_random_command(message: Message, command: CommandObject) -> None:
    if message.from_user.id != ADMIN_ID:
        return

    min_val, max_val = 50, 90

    # If the admin passes custom range bounds (e.g., /reset_random 60 80)
    if command.args:
        try:
            args = command.args.split()
            if len(args) == 2:
                min_val = int(args[0])
                max_val = int(args[1])
                if min_val > max_val:
                    min_val, max_val = max_val, min_val
        except ValueError:
            await message.answer(
                "⚠️ <b>Error:</b> Arguments must be numbers. Example: <code>/reset_random 60 80</code>", 
                parse_mode="HTML"
            )
            return

    new_count = await StatsRepository.set_random_today_count(min_val, max_val)

    await message.answer(
        f"✅ <b>Today's analysis counter updated!</b>\n\n"
        f"🎲 New random value (range {min_val}–{max_val}): <b>{new_count}</b>",
        parse_mode="HTML"
    )
    
@router.message(Command("add_score"))
async def add_score_command(message: Message, command: CommandObject, state: FSMContext) -> None:
    if message.from_user.id != ADMIN_ID:
        return

    if not command.args:
        await message.answer("⚠️ <b>Usage:</b> <code>/add_score F 8.21 D 2.10</code>", parse_mode="HTML")
        return

    try:
        args = command.args.split()
        f_score = float(args[1])
        d_score = float(args[3])

        await state.update_data(admin_force_f=f_score, admin_force_d=d_score)
        await message.answer(f"✅ <b>Custom scores set for next photo:</b>\nFeatures: {f_score}\nDimorphism: {d_score}", parse_mode="HTML")
    except (IndexError, ValueError):
        await message.answer("⚠️ <b>Error:</b> Incorrect format. Use <code>/add_score F 8.21 D 2.10</code>", parse_mode="HTML")

@router.message(Command("skip_quality"))
async def skip_quality_command(message: Message, state: FSMContext) -> None:
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(skip_check=True)
    await message.answer("✅ <b>Quality check disabled for your next photo.</b>", parse_mode="HTML")

@router.message(Command("discount_zero"))
async def discount_zero_command(message: Message, command: CommandObject) -> None:
    if message.from_user.id != ADMIN_ID:
        return
        
    if not command.args:
        await message.answer("⚠️ <b>Usage:</b> <code>/discount_zero <user_id></code>", parse_mode="HTML")
        return
        
    try:
        target_user_id = int(command.args.strip())
    except ValueError:
        await message.answer("⚠️ <b>Error:</b> user_id must be a number.", parse_mode="HTML")
        return
        
    result_msg = await UserRepository.admin_zero_discount(target_user_id)
    await message.answer(result_msg, parse_mode="HTML")

@router.message(Command("discount_add"))
async def discount_add_command(message: Message, command: CommandObject) -> None:
    if message.from_user.id != ADMIN_ID:
        return
        
    if not command.args:
        await message.answer("⚠️ <b>Usage:</b> <code>/discount_add <user_id></code>", parse_mode="HTML")
        return
        
    try:
        target_user_id = int(command.args.strip())
    except ValueError:
        await message.answer("⚠️ <b>Error:</b> user_id must be a number.", parse_mode="HTML")
        return
        
    result_msg = await UserRepository.admin_add_discount(target_user_id)
    await message.answer(result_msg, parse_mode="HTML")
    
@router.message(Command("add_tries"))
async def add_tries_command(message: Message, command: CommandObject, bot: Bot) -> None:
    if message.from_user.id != ADMIN_ID:
        return
    
    if command.args is None:
        await message.answer("⚠️ <b>Usage:</b> <code>/add_tries &lt;user_id&gt; &lt;amount&gt;</code>", parse_mode="HTML")
        return
        
    try:
        args = command.args.split()
        if len(args) != 2:
            await message.answer("⚠️ <b>Usage:</b> <code>/add_tries &lt;user_id&gt; &lt;amount&gt;</code>", parse_mode="HTML")
            return
            
        target_user_id = int(args[0])
        amount = int(args[1])
        
    except ValueError:
        await message.answer("⚠️ <b>Error:</b> Both user_id and amount must be numbers.", parse_mode="HTML")
        return

    new_balance = await UserRepository.add_balance(target_user_id, amount=amount)
    
    await message.answer(
        f"✅ <b>Success!</b> Added {amount} analyses to user <code>{target_user_id}</code>.\n"
        f"New Balance: {new_balance}",
        parse_mode="HTML"
    )

    try:
        is_or_es = "is" if amount == 1 else "es"
        user_msg = (
            f"🎉 <b>Balance updated!</b>\n\n"
            f"You received <b>{amount}</b> new analys{is_or_es}. "
            f"Your total balance is now <b>{new_balance}</b>.\n\n"
            f"📸 <b>How to take the perfect photo(like in the example of full analysis):</b>\n"
            f"• <b>Camera:</b> Ask a friend to take your picture using the main (rear) camera, or take a photo at arm's length. Set zoom to <b>x2</b> to prevent face distortion.\n"
            f"• <b>Position:</b> Keep the camera <b>exactly at eye level</b> and look straight into the lens.\n"
            f"• <b>Lighting:</b> Face a bright, even light source directly (like a window). Avoid harsh shadows on one side of your face.\n\n"
            f"💡 <i>Tip: Our AI is very strict to ensure mathematical accuracy. If your photos keep getting rejected, simply move to a brighter location. If the system rejects all your attempts, don't worry — you can always skip the check after 3 bad attepts or contact our support!</i>\n\n"
            f"Send your photo below to begin 👇"
        )
        await bot.send_message(
            chat_id=target_user_id,
            text=user_msg,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"[ERROR] Could not notify user {target_user_id} about added tries: {e}")

@router.message(Command("check_number"))
async def check_number_command(message: Message, command: CommandObject) -> None:
    if message.from_user.id != ADMIN_ID:
        return

    if command.args is None:
        await message.answer("⚠️ <b>Usage:</b> <code>/check_number &lt;user_id&gt;</code>", parse_mode="HTML")
        return

    try:
        target_user_id = int(command.args.strip())
    except ValueError:
        await message.answer("⚠️ <b>Error:</b> user_id must be a number.", parse_mode="HTML")
        return

    user = await UserRepository.get_user_info(target_user_id)
    if user is None:
        await message.answer(
            f"❌ User <code>{target_user_id}</code> was not found in the database.",
            parse_mode="HTML"
        )
        return

    await message.answer(
        f"📊 <b>User info</b> — <code>{target_user_id}</code>\n\n"
        f"💳 Balance: <b>{user.balance}</b> analyses\n"
        f"✅ Completed analyses: <b>{user.total_analyses_done}</b>\n"
        f"🛒 Total purchased: <b>{user.total_purchased}</b>",
        parse_mode="HTML"
    )

@router.message(Command("minus_tries"))
async def minus_tries_command(message: Message, command: CommandObject) -> None:
    if message.from_user.id != ADMIN_ID:
        return

    if command.args is None:
        await message.answer("⚠️ <b>Usage:</b> <code>/minus_tries &lt;user_id&gt; &lt;amount&gt;</code>", parse_mode="HTML")
        return

    try:
        args = command.args.split()
        if len(args) != 2:
            await message.answer("⚠️ <b>Usage:</b> <code>/minus_tries &lt;user_id&gt; &lt;amount&gt;</code>", parse_mode="HTML")
            return

        target_user_id = int(args[0])
        amount = int(args[1])

    except ValueError:
        await message.answer("⚠️ <b>Error:</b> Both user_id and amount must be numbers.", parse_mode="HTML")
        return

    if amount <= 0:
        await message.answer("⚠️ <b>Error:</b> amount must be a positive number.", parse_mode="HTML")
        return

    new_balance = await UserRepository.subtract_balance(target_user_id, amount=amount)

    if new_balance is None:
        await message.answer(
            f"❌ User <code>{target_user_id}</code> was not found in the database.",
            parse_mode="HTML"
        )
        return

    await message.answer(
        f"✅ <b>Success!</b> Removed up to {amount} analyses from user <code>{target_user_id}</code>.\n"
        f"New Balance: {new_balance}",
        parse_mode="HTML"
    )

@router.message(Command("add_number"))
async def add_number_command(message: Message, command: CommandObject) -> None:
    if message.from_user.id != ADMIN_ID:
        return
    
    if command.args is None:
        await message.answer("⚠️ <b>Usage:</b> <code>/add_number &lt;amount&gt;</code>\nExample: <code>/add_number 10</code>", parse_mode="HTML")
        return
        
    try:
        amount = int(command.args.strip())
    except ValueError:
        await message.answer("⚠️ <b>Error:</b> The amount must be a number.", parse_mode="HTML")
        return

    new_total = await StatsRepository.add_to_today_count(amount)
    
    await message.answer(
        f"✅ <b>Success!</b> Added <b>{amount}</b> analyses.\n\n"
        f"📈 Updated statistics:\n"
        f"Today users performed: <b>{new_total}</b> analyses",
        parse_mode="HTML"
    )

@router.message(Command("stats"))
async def stats_command(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        return

    try:
        total_users = await UserRepository.get_total_users_count()
        stats = await UserRepository.get_payment_stats()
        mini_stats = await MiniAnalysisRepository.get_mini_stats() 
        traffic_stats = await UserRepository.get_traffic_stats()

        traffic_text = "\n".join([f"  • {src}: <b>{count}</b>" for src, count in traffic_stats.items()])

        text = (
            "📊 <b>Project Statistics</b>\n\n"
            f"👥 <b>Total unique users:</b> {total_users}\n\n"
            f"🚀 <b>Traffic Sources:</b>\n{traffic_text}\n\n"
            f"🎁 <b>Total Mini-Analyses:</b> {mini_stats['completed']}\n\n"
            "💳 <b>[1 Analysis] Package Sales (2.98):</b>\n"
            f"  • Official Payment (Tribute): <b>{stats.get('tribute_1', 0)}</b>\n"
            f"  • Manual Donation: <b>{stats.get('donation_1', 0)}</b>\n"
            f"  👉 <i>Total 1 Analysis: {stats.get('tribute_1', 0) + stats.get('donation_1', 0)}</i>\n\n"
            "💳 <b>[3 Analyses] Package Sales (6.98):</b>\n"
            f"  • Official Payment (Tribute): <b>{stats.get('tribute_3', 0)}</b>\n"
            f"  • Manual Donation: <b>{stats.get('donation_3', 0)}</b>\n"
            f"  👉 <i>Total 3 Analyses: {stats.get('tribute_3', 0) + stats.get('donation_3', 0)}</i>\n"
        )
        
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch stats: {e}")
        await message.answer("⚠️ <b>Error:</b> Failed to load statistics. Please check the logs.", parse_mode="HTML")

@router.message(Command("clear_stats"))
async def clear_stats_command(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        return

    try:
        await UserRepository.clear_all_stats()
        await StatsRepository.reset_today_count()
        
        await message.answer("✅ <b>All statistics have been successfully cleared!</b>\nPurchase counters and daily active stats have been reset to zero.", parse_mode="HTML")
    except Exception as e:
        logger.error(f"[ERROR] Failed to clear stats: {e}")
        await message.answer("⚠️ <b>Error:</b> Failed to clear statistics. Please check the logs.", parse_mode="HTML")
        
@router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject) -> None:
    # Отримуємо джерело з deep link (t.me/bot?start=tiktok)
    traffic_source = command.args.strip()[:32] if command.args else None

    user = await UserRepository.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        source=traffic_source
    )

    today_count = await StatsRepository.get_today_count()
    free_mini_balance = await MiniAnalysisRepository.get_free_balance(message.from_user.id)

    is_active, mins, secs = await UserRepository.get_discount_status(user.telegram_id)
    
    promo_text = ""
    if is_active:
        # Акція активна — показуємо таймер зворотного відліку
        promo_text = "\n\n" + en.MAIN_MENU_PROMO_ACTIVE.format(mins=mins, secs=secs)
    elif user.discount_offered_at is None and free_mini_balance > 0:
        # Знижка ще НІКОЛИ не пропонувалася І є безкоштовні спроби
        promo_text = "\n\n" + en.MAIN_MENU_PROMO_BEFORE

    main_text = (
        "📍 <b>Main menu:</b>\n\n"
        "☑️ <b>bp_guide AI</b> mathematically evaluates how harmonious your facial features are.\n\n"
        f"<blockquote>Your balance: <b>{user.balance}</b> analyses\n\n"
        f"Today users performed: <b>{today_count}</b> analyses</blockquote>"
        f"{promo_text}\n\n"
        "⬇️ Below — examples of full analysis."
    )
    
    await message.answer(
        main_text,
        reply_markup=start_keyboard(show_free_mini=free_mini_balance > 0),
        parse_mode="HTML"
    )

    if os.path.exists(settings.example_pdf_path):
        await message.answer_document(FSInputFile(settings.example_pdf_path))
    else:
        logger.warning(f"[WARN] Example PDF not found at {settings.example_pdf_path}.")


@router.message(Command("send_message_all"))
async def broadcast_command(message: Message, command: CommandObject, bot: Bot) -> None:
    if message.from_user.id != ADMIN_ID:
        return

    if command.args is None:
        await message.answer("⚠️ <b>Usage:</b> <code>/send_message_all &lt;Your text here&gt;</code>\nExample: <code>/send_message_all Today special offer!!</code>", parse_mode="HTML")
        return

    broadcast_text = command.args
    await message.answer(f"⏳ <b>Broadcasting started...</b>\n\nText:\n{broadcast_text}", parse_mode="HTML")

    try:
        users_ids = await UserRepository.get_all_user_ids() 
    except AttributeError:
        await message.answer("❌ Error: 'get_all_user_ids' method not found in UserRepository. Please add it first.")
        return

    success_count = 0
    fail_count = 0

    for user_id in users_ids:
        try:
            await bot.send_message(chat_id=user_id, text=broadcast_text, parse_mode="HTML")
            success_count += 1
            await asyncio.sleep(0.05) 
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            await bot.send_message(chat_id=user_id, text=broadcast_text, parse_mode="HTML")
            success_count += 1
        except Exception:
            fail_count += 1

    await message.answer(
        f"✅ <b>Broadcast finished!</b>\n\n"
        f"📩 Delivered: <b>{success_count}</b>\n"
        f"❌ Failed (Blocked bot etc): <b>{fail_count}</b>",
        parse_mode="HTML"
    )