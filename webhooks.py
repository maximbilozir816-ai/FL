# webhooks.py
import hashlib
import hmac
import logging
from typing import Optional

from fastapi import APIRouter, Request, Header
from fastapi.responses import JSONResponse
from aiogram import Bot

from config import settings
from database.repository import UserRepository
from texts import en

logger = logging.getLogger(__name__)
router = APIRouter()

# Bot instance will be injected from bot.py during startup
bot: Bot = None

# Tribute sends `product_id` (an integer) with every new_digital_product /
# digital_product_refunded webhook. Mapping by product_id is the only
# reliable way to know which package was bought -- Tribute amounts are in
# the *smallest currency unit* (cents), can change if you edit the price in
# the dashboard, and can come in different currencies (USD/EUR/RUB), so
# guessing the package from `amount` is fragile. Fill these from your
# Tribute dashboard (Products -> your product -> id in the URL, or via
# GET https://tribute.tg/api/v1/products with your Api-Key).
PRODUCT_CREDITS: dict[int, int] = {}
if settings.tribute_product_id_1:
    PRODUCT_CREDITS[settings.tribute_product_id_1] = 1
if settings.tribute_product_id_3:
    PRODUCT_CREDITS[settings.tribute_product_id_3] = 3


def verify_signature(raw_body: bytes, signature: str | None) -> bool:
    """Verify Tribute's trbt-signature header (HMAC-SHA256 over raw body)."""
    if not signature or not settings.tribute_api_key:
        return False
    expected = hmac.new(
        key=settings.tribute_api_key.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _error_response(message: str, status_code: int = 500) -> JSONResponse:
    """
    BUGFIX: previously every error path returned a plain dict, which FastAPI
    serializes with an implicit HTTP 200. Tribute only retries a webhook
    delivery it considers *failed* (non-2xx), so a DB error, a messaging
    error, or any other internal failure was silently swallowed -- Tribute
    saw "200 OK" and never retried, permanently losing that payment credit.
    This helper makes sure failures actually surface as non-2xx responses.
    """
    return JSONResponse(status_code=status_code, content={"status": "error", "message": message})


def _currency_ok(payload_currency: Optional[str]) -> bool:
    """True if the webhook's currency matches what we expect our products to
    be priced in. Used to gate amount-based guessing (see _resolve_credits
    and the donation-matching branch below) -- comparing raw cent values
    across different currencies can silently misclassify a payment."""
    if not payload_currency:
        return False
    return payload_currency.strip().upper() == settings.expected_currency.strip().upper()


def _resolve_credits(payload: dict) -> Optional[int]:
    """
    Maps a webhook payload to a number of analyses, product_id first.

    BUGFIX: the amount-based fallback (used only when product_id is
    unknown/unmapped) previously guessed the package from raw cent value
    alone, ignoring currency. It now returns None ("uncertain, needs manual
    review") instead of silently guessing whenever the currency doesn't
    match `settings.expected_currency` -- the caller must not auto-credit
    in that case.
    """
    product_id = payload.get("product_id")
    if product_id in PRODUCT_CREDITS:
        return PRODUCT_CREDITS[product_id]

    logger.warning(
        f"[WARN] Unknown Tribute product_id={product_id}, falling back to amount-based guess. "
        f"Add it to TRIBUTE_PRODUCT_ID_1 / TRIBUTE_PRODUCT_ID_3 in your env."
    )

    if not _currency_ok(payload.get("currency")):
        logger.warning(
            f"[WARN] Cannot safely guess package: currency={payload.get('currency')!r} "
            f"does not match expected {settings.expected_currency!r}. Needs manual review."
        )
        return None

    # Tribute amounts are in the smallest currency unit (cents), NOT dollars.
    amount_cents = int(payload.get("amount") or 0)
    return 3 if amount_cents > 700 else 1


async def _notify_admin_manual_review(telegram_id, amount_cents: int, currency: Optional[str], reason: str) -> None:
    if not bot:
        return
    try:
        await bot.send_message(
            chat_id=settings.admin_id,
            text=(
                f"⚠️ <b>Payment needs manual review</b>\n\n"
                f"Reason: {reason}\n"
                f"User ID: <code>{telegram_id}</code>\n"
                f"Amount: {amount_cents / 100:.2f} {str(currency).upper() if currency else 'UNKNOWN'}\n\n"
                f"Run: <code>/add_tries {telegram_id} 1</code> (or the right amount)"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"[ERROR] Failed to notify admin about payment needing manual review: {e}")


@router.post("/api/tribute-webhook")
async def tribute_payment_webhook(
    request: Request,
    trbt_signature: str | None = Header(default=None, alias="trbt-signature"),
):
    raw_body = await request.body()

    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"[ERROR] Failed to parse Tribute webhook JSON: {e}")
        return _error_response("Invalid JSON", status_code=400)

    # ВАЖЛИВО: Пропуск тестової події від Tribute без підпису
    if data.get("test_event") == "test_event":
        logger.info("[INFO] Received Tribute test_event, returning 200 OK")
        return JSONResponse(status_code=200, content={"status": "ok"})

    # Перевірка підпису HMAC для всіх реальних транзакцій
    if not verify_signature(raw_body, trbt_signature):
        logger.warning("[WARN] Invalid or missing Tribute webhook signature")
        return _error_response("Invalid signature", status_code=401)

    logger.info(f"[INFO] Received webhook from Tribute: {data}")

    event_name = data.get("name")
    payload = data.get("payload", {})
    purchase_id = payload.get("purchase_id")
    telegram_id = payload.get("telegram_user_id")

    if event_name == "new_digital_product":
        if not telegram_id:
            logger.error(f"[ERROR] Missing telegram_user_id in payload: {payload}")
            return _error_response("Missing telegram_user_id", status_code=400)

        try:
            analyses_to_add = _resolve_credits(payload)

            if analyses_to_add is None:
                # Currency mismatch and no known product_id -- do NOT guess.
                amount_cents = int(payload.get("amount") or 0)
                await _notify_admin_manual_review(
                    telegram_id, amount_cents, payload.get("currency"),
                    "unknown product_id + unexpected currency",
                )
                return JSONResponse(status_code=200, content={"status": "ok"})

            new_balance = await UserRepository.credit_payment(
                telegram_id=int(telegram_id),
                credit_amount=analyses_to_add,
                amount_cents=payload.get("amount"),
                currency=payload.get("currency"),
                payment_ref=str(purchase_id) if purchase_id is not None else f"nopid:{telegram_id}:{data}",
                provider_ref=str(payload.get("transaction_id")),
            )

            if new_balance is None:
                logger.info(f"[INFO] Purchase {purchase_id} already processed, skipping")
                return JSONResponse(status_code=200, content={"status": "ok"})

            logger.info(
                f"[INFO] 💰 PAYMENT SUCCESS | Telegram ID: {telegram_id} | "
                f"Added: {analyses_to_add} | Purchase: {purchase_id} | New balance: {new_balance}"
            )

            if bot:
                try:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=en.payment_success(new_balance),
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.error(f"[ERROR] Failed to send payment success message to {telegram_id}: {e}")

        except Exception as e:
            logger.error(f"[ERROR] Database or messaging error during payment processing: {e}", exc_info=True)
            return _error_response("Internal processing error", status_code=500)

    elif event_name == "digital_product_refunded":
        if not telegram_id:
            logger.error(f"[ERROR] Missing telegram_user_id in refund payload: {payload}")
            return _error_response("Missing telegram_user_id", status_code=400)

        try:
            analyses_to_remove = _resolve_credits(payload)
            if analyses_to_remove is None:
                await _notify_admin_manual_review(
                    telegram_id, int(payload.get("amount") or 0), payload.get("currency"),
                    "refund with unknown product_id + unexpected currency",
                )
                return JSONResponse(status_code=200, content={"status": "ok"})

            logger.info(f"[INFO] Refund event for purchase {purchase_id}, telegram_id={telegram_id}")
            await UserRepository.add_balance(int(telegram_id), amount=-analyses_to_remove)
        except Exception as e:
            logger.error(f"[ERROR] Failed to process refund: {e}", exc_info=True)
            return _error_response("Internal processing error", status_code=500)

    elif event_name == "new_donation":
        donation_id = payload.get("donation_request_id")
        if not telegram_id:
            logger.warning(f"[WARN] Donation with no telegram_user_id (likely paid anonymously/outside Telegram): {payload}")
            return JSONResponse(status_code=200, content={"status": "ok"})

        try:
            amount_cents = int(payload.get("amount") or 0)
            currency = payload.get("currency")
            tol = settings.donation_amount_tolerance_cents

            # Додаємо визначення акційної ціни $2.89 (289 центів)
            discount_price_1_cents = 289

            analyses_to_add = None
            if _currency_ok(currency):
                if abs(amount_cents - settings.donation_price_1_cents) <= tol:
                    analyses_to_add = 1
                elif abs(amount_cents - discount_price_1_cents) <= tol:
                    # Якщо оплачено $2.89 — перевіряємо, чи має користувач право на знижку (активний таймер або grace-період)
                    has_discount = await UserRepository.check_discount_grace_period(int(telegram_id))
                    if has_discount:
                        analyses_to_add = 1
                elif abs(amount_cents - settings.donation_price_3_cents) <= tol:
                    analyses_to_add = 3

            dedup_key = f"donation:{donation_id}:{amount_cents}:{telegram_id}"

            if analyses_to_add is None:
                logger.warning(
                    f"[WARN] Donation amount {amount_cents} cents ({currency}) from telegram_id={telegram_id} "
                    f"doesn't match a known package/currency. Needs manual review."
                )
                try:
                    await UserRepository.record_payment(
                        telegram_id=int(telegram_id), amount=amount_cents,
                        currency=currency,
                        telegram_payment_charge_id=dedup_key,
                        provider_payment_charge_id=None,
                    )
                except Exception:
                    pass
                await _notify_admin_manual_review(telegram_id, amount_cents, currency, "unmatched donation amount/currency")
                return JSONResponse(status_code=200, content={"status": "ok"})

            new_balance = await UserRepository.credit_payment(
                telegram_id=int(telegram_id),
                credit_amount=analyses_to_add,
                amount_cents=amount_cents,
                currency=currency,
                payment_ref=dedup_key,
                provider_ref=None,
                mark_discount_used=False
            )

            if new_balance is None:
                logger.info(f"[INFO] Donation {dedup_key} already processed, skipping")
                return JSONResponse(status_code=200, content={"status": "ok"})

            logger.info(
                f"[INFO] 💰 DONATION MATCHED | Telegram ID: {telegram_id} | "
                f"Added: {analyses_to_add} | New balance: {new_balance}"
            )
            if bot:
                try:
                    await bot.send_message(
                        chat_id=telegram_id, text=en.payment_success(new_balance), parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"[ERROR] Failed to send payment success message to {telegram_id}: {e}")

        except Exception as e:
            logger.error(f"[ERROR] Failed to process donation: {e}", exc_info=True)
            return _error_response("Internal processing error", status_code=500)

    else:
        logger.info(f"[INFO] Unhandled webhook event: {event_name}")

    return JSONResponse(status_code=200, content={"status": "ok"})