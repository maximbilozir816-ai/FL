# config.py
"""
Central configuration. All values are pulled from environment variables so
the same code base can run in dev / staging / prod without edits.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    val = os.getenv(name)
    return int(val) if val else default


@dataclass(frozen=True)
class Settings:
    # --- Telegram ---
    bot_token: str = os.getenv("BOT_TOKEN", "")

    # --- Database ---
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")

    # --- OpenAI ---
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # --- Payments (Tribute) ---
    # IMPORTANT: these must come from "digital" (ready-made) products in
    # Tribute, from GET /products:
    #   - tribute_pay_url*      -> the `webLink` field (web.tribute.tg/p/xxx).
    #                              This is the ONLY way to offer card/SBP for
    #                              a digital product -- Telegram's Bot
    #                              Payments policy forces the in-bot `link`
    #                              (t.me/tribute/app?startapp=...) to be
    #                              Stars-only for any digital/virtual good,
    #                              Tribute cannot bypass that. webLink still
    #                              opens inside Telegram's built-in browser,
    #                              not a separate app, and fires the exact
    #                              same new_digital_product webhook.
    #   - tribute_stars_pay_url* -> optional, the `link` field, if you also
    #                              want to offer a one-tap Stars button.
    # "Custom" (На замовлення) products require manual fulfillment -- don't
    # use them for either link.
    tribute_pay_url: str = os.getenv("TRIBUTE_PAY_URL", "")
    tribute_pay_url_3: str = os.getenv("TRIBUTE_PAY_URL_3", "")
    tribute_stars_pay_url: str = os.getenv("TRIBUTE_STARS_PAY_URL", "")
    tribute_stars_pay_url_3: str = os.getenv("TRIBUTE_STARS_PAY_URL_3", "")
    tribute_api_key: str = os.getenv("TRIBUTE_API_KEY", "")  # kept, used for HMAC + webhook

    # --- Fallback manual payment (Tribute Donations) ---
    # For users who can't complete the web/app checkout (blocked region, card
    # issues, etc). They donate any amount via this link; if the amount
    # matches a known price (within DONATION_AMOUNT_TOLERANCE_CENTS) we credit
    # automatically from the new_donation webhook, same as digital products.
    # If it doesn't match, the admin gets notified and credits manually with
    # /add_tries -- no purchase is ever silently lost.
    tribute_donation_url: str = os.getenv("TRIBUTE_DONATION_URL", "")
    donation_price_1_cents: int = _get_int("DONATION_PRICE_1_CENTS", 598)
    donation_price_3_cents: int = _get_int("DONATION_PRICE_3_CENTS", 998)
    donation_amount_tolerance_cents: int = _get_int("DONATION_AMOUNT_TOLERANCE_CENTS", 50)
    admin_id: int = _get_int("ADMIN_ID", 5086065826)

    # Numeric Tribute product IDs (the `id` field from GET /products), used
    # by webhooks.py to reliably map a payment to a credit amount instead of
    # guessing from `amount` (which Tribute sends in cents, not dollars).
    tribute_product_id_1: int = _get_int("TRIBUTE_PRODUCT_ID_1", 0)
    tribute_product_id_3: int = _get_int("TRIBUTE_PRODUCT_ID_3", 0)

    # BUGFIX: the amount-based fallback (used only when product_id is
    # unknown) compared raw cent values without checking currency, so a
    # payment in a different currency with a numerically similar amount
    # could be misclassified into the wrong package. webhooks.py now only
    # trusts the amount-based guess when payload currency matches this
    # (case-insensitively); otherwise it flags the payment for manual
    # admin review instead of guessing.
    expected_currency: str = os.getenv("EXPECTED_CURRENCY", "USD")

    # --- Feature flags ---
    quality_gate_enabled: bool = _get_bool("QUALITY_GATE_ENABLED", True)
    ai_analysis_enabled: bool = _get_bool("AI_ANALYSIS_ENABLED", True)
    process_batch_photos: bool = _get_bool("PROCESS_BATCH_PHOTOS", False)

    # --- Misc ---
    example_pdf_path: str = os.getenv("EXAMPLE_PDF_PATH", "assets/face_analysis.pdf")
    support_channel: str = os.getenv("SUPPORT_CHANNEL", "@bp_guide_scoringAI_bot")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()