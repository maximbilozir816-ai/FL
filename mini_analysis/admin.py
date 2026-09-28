from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from config import settings

from mini_analysis import texts as mtexts
from mini_analysis.repository import MiniAnalysisRepository

logger = logging.getLogger(__name__)
router = Router(name="mini_analysis_admin")

ADMIN_ID = settings.admin_id


@router.message(Command("add_minitries"))
async def add_minitries_command(message: Message, command: CommandObject, bot: Bot) -> None:
    if message.from_user.id != ADMIN_ID:
        return

    if command.args is None:
        await message.answer(
            "⚠️ <b>Usage:</b> <code>/add_minitries &lt;user_id&gt; &lt;amount&gt;</code>", parse_mode="HTML"
        )
        return

    try:
        args = command.args.split()
        if len(args) != 2:
            raise ValueError
        target_user_id = int(args[0])
        amount = int(args[1])
    except ValueError:
        await message.answer("⚠️ <b>Error:</b> Both user_id and amount must be numbers.", parse_mode="HTML")
        return

    new_balance = await MiniAnalysisRepository.add_free_tries(target_user_id, amount=amount)

    if new_balance is None:
        await message.answer(
            f"❌ User <code>{target_user_id}</code> was not found in the database.", parse_mode="HTML"
        )
        return

    await message.answer(
        f"✅ <b>Success!</b> Added {amount} free mini-analysis tries to user <code>{target_user_id}</code>.\n"
        f"New free tries: {new_balance}",
        parse_mode="HTML",
    )

    try:
        await bot.send_message(
            chat_id=target_user_id,
            text=mtexts.mini_tries_granted_notice(amount),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"[ERROR] Could not notify user {target_user_id} about added mini tries: {e}")
