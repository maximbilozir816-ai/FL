from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from mini_analysis import texts as mtexts
from mini_analysis.constants import CB_GET_MINI_ANALYSIS, CB_SKIP_MINI_QUALITY_CHECK


def free_mini_analysis_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text=mtexts.BTN_FREE_MINI_ANALYSIS, callback_data=CB_GET_MINI_ANALYSIS)


def mini_skip_check_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=mtexts.BTN_SKIP_MINI_CHECK, callback_data=CB_SKIP_MINI_QUALITY_CHECK))
    return builder.as_markup()
