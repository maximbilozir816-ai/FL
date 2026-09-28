# keyboards/inline.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from texts import en

CB_GET_ANALYSIS = "get_analysis"
CB_GET_FULL_ANALYSIS_1 = "get_full_analysis_1"
CB_GET_FULL_ANALYSIS_3 = "get_full_analysis_3"
CB_BACK_TO_START = "back_to_start"
CB_GET_HELP = "get_help"
CB_PROJECT_OVERVIEW = "project_overview"
CB_MANUAL_PAYMENT = "manual_payment"

def back_only_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=en.BTN_BACK, callback_data=CB_BACK_TO_START))
    return builder.as_markup()

def start_keyboard(show_free_mini: bool = False):
    builder = InlineKeyboardBuilder()

    # Перший ряд: Одна велика кнопка
    builder.row(InlineKeyboardButton(
        text="💎 Get Full face analysis ›",
        callback_data=CB_GET_ANALYSIS
    ))

    # --- NEW: optional free mini-analysis button --------------------------
    # Only rendered when the caller (handlers/start.py, handlers/callbacks.py)
    # has confirmed the user still has free tries left. Button definition
    # itself lives in mini_analysis/keyboards.py to keep this file clean;
    # imported locally to avoid any import-order surprises at module load.
    if show_free_mini:
        from mini_analysis.keyboards import free_mini_analysis_button
        builder.row(free_mini_analysis_button())
    # ------------------------------------------------------------------------

    # Другий ряд: Дві кнопки в один рядок
    builder.row(
        InlineKeyboardButton(
            text="Support ›",
            callback_data=CB_GET_HELP
        ),
        InlineKeyboardButton(
            text="About the Project ›",
            callback_data=CB_PROJECT_OVERVIEW
        )
    )

    return builder.as_markup()

def details_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Дві кнопки вибору пакету аналізів
    builder.add(InlineKeyboardButton(text=en.BTN_GET_FULL_ANALYSIS_1, callback_data=CB_GET_FULL_ANALYSIS_1))
    builder.add(InlineKeyboardButton(text=en.BTN_GET_FULL_ANALYSIS_3, callback_data=CB_GET_FULL_ANALYSIS_3))
    builder.add(InlineKeyboardButton(text=en.BTN_BACK, callback_data=CB_BACK_TO_START))
    builder.adjust(1)
    return builder.as_markup()


def payment_keyboard(
    tribute_url: str | None = None,
    tribute_stars_url: str | None = None,
    package_count: int = 1,
    discount_active: bool = False,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Динамічні тексти кнопок залежно від наявності знижки
    if discount_active and package_count == 1:
        btn_card_text = "💳 Pay by card / SBP (Text Admin for a discount)"
        btn_donation_text = "🔥 Pay by donation (Automatical discount)"
    else:
        btn_card_text = en.BTN_PAY_CARD
        btn_donation_text = en.BTN_CANT_PAY

    if tribute_url:
        builder.add(InlineKeyboardButton(text=btn_card_text, url=tribute_url))
    
    if tribute_stars_url:
        builder.add(InlineKeyboardButton(text=en.BTN_PAY_STARS, url=tribute_stars_url))

    builder.add(InlineKeyboardButton(text=btn_donation_text, callback_data=f"{CB_MANUAL_PAYMENT}:{package_count}"))
    builder.add(InlineKeyboardButton(text=en.BTN_BACK, callback_data=CB_GET_ANALYSIS))
    
    builder.adjust(1)
    return builder.as_markup()


def manual_payment_keyboard(donation_url: str | None, package_count: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if donation_url:
        builder.add(InlineKeyboardButton(text=en.BTN_DONATE, url=donation_url))

    if str(package_count) == "3":
        back_callback = CB_GET_FULL_ANALYSIS_3
    else:
        back_callback = CB_GET_FULL_ANALYSIS_1

    builder.add(InlineKeyboardButton(text=en.BTN_BACK, callback_data=back_callback))
    builder.adjust(1)
    return builder.as_markup()


def buy_more_keyboard(btn_1_text: str = None) -> InlineKeyboardMarkup:
    if btn_1_text is None:
        btn_1_text = en.BTN_GET_FULL_ANALYSIS_1
        
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=btn_1_text, callback_data=CB_GET_FULL_ANALYSIS_1))
    builder.add(InlineKeyboardButton(text=en.BTN_GET_FULL_ANALYSIS_3, callback_data=CB_GET_FULL_ANALYSIS_3))
    builder.adjust(1)
    return builder.as_markup()
