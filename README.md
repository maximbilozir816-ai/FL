# Face Aura Bot -- Production Refactor

## 1. New directory structure

```
project/
├── main.py                      # Composition root: creates bot/dispatcher, registers routers, starts polling
├── config.py                    # All settings, read from env vars (.env)
├── requirements.txt
├── .env.example
├── database/
│   ├── models.py                 # SQLAlchemy models: User, Payment, DailyStat
│   ├── engine.py                 # Async engine/session factory + init_db()
│   └── repository.py             # UserRepository (atomic balance ops), StatsRepository
├── texts/
│   └── en.py                     # All user-facing copy (single source, easy to localize later)
├── keyboards/
│   └── inline.py                 # All inline keyboards / callback_data constants
├── handlers/                     # Thin, aiogram Router-based, one concern each
│   ├── start.py                  # /start
│   ├── callbacks.py              # "Get Analysis" / "Get Full Analysis" / payment screen
│   ├── payment.py                # pre_checkout_query + successful_payment
│   └── photo.py                  # Orchestrates the photo pipeline (balance, status edits, error handling)
├── services/                     # The former "god object" photo.py, split by concern
│   ├── photo_processor.py        # download validation -> face detection -> quality gate -> crop -> TTA
│   └── report_builder.py         # metrics -> AI payload -> overview contexts -> PDF bytes
└── face/                         # Kept mostly as-is; only comments/logging cleaned up
    ├── ai_analyzer.py            # Prompt relaxed from hard character counts to word-count targets
    ├── pdf_report.py
    ├── report_order.py
    ├── tta.py                    # Debug block removed
    ├── metrics/
    │   ├── alignment.py
    │   ├── base.py
    │   ├── geometry.py
    │   ├── confidence/
    │   │   ├── lighting.py
    │   │   └── pose.py
    │   └── features/
    │       ├── Overall_score.py
    │       └── overall_impression.py
    └── templates/
        ├── report.html
        ├── nose_metrics.html
        └── special_metrics_block.html
```

## 2. Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in BOT_TOKEN, OPENAI_API_KEY, etc.
python main.py
```

The database is created automatically on first run (`init_db()` in `main.py`).

## 3. Files you should delete from the old project

- **`quality_gate.py`** -- fully in Ukrainian, unused by the actual pipeline. `photo.py` (and now `services/photo_processor.py`) always used `face.metrics.confidence.analyze_total_confidence` (which wraps `lighting.py` + `pose.py`) for the real quality gate. `quality_gate.py` was dead code duplicating that with a cruder blur/brightness check. Safe to delete.
- **The old `handlers/photo.py`, `handlers/start.py`** -- replaced by the versions in this package.
- **Any in-memory balance dict / user-state module** you were using before (e.g. a `user_states = {}` global) -- fully replaced by `database/repository.py`. If you had a module like `state.py` or `balances.py` holding this in memory, delete it.
- **Old `.py` files with Ukrainian log/user-facing strings** you don't see listed above -- I could only clean the files you sent me (listed below). Anything else with Cyrillic text still needs the same treatment.

## 4. Files kept, with only light edits

`pdf_report.py`, `report_order.py`, `alignment.py`, `base.py`, `geometry.py`, `lighting.py`, `pose.py`, `Overall_score.py`, `overall_impression.py`, `tta.py` (debug block removed), the three `.html` templates -- all copied over with Ukrainian comments translated to English and (for `tta.py`) the verbose per-request debug logging removed.

## 5. What I did NOT touch / could not verify

I only had 17 of your files. These are imported by the refactored services but I never saw their contents, so I preserved the import paths and public function signatures exactly as `photo.py` used them, on the assumption they're unchanged:

- `face/cropper.py` (`smart_face_crop`, `CropConfig`)
- `face/utils/*` (`get_user_concurrency_manager`, `get_pdf_executor`, `get_temp_manager`)
- `face/metrics/__init__.py` (`get_all_metrics`)
- `face/metrics/confidence/__init__.py` (`analyze_total_confidence`)
- `face/metrics/scoring.py` (`compute_score`)
- `face/metrics/features/__init__.py` (`ACTIVE_METRICS`)
- `face/metrics/features/{eye_area,facialbalance,lips,nose,brows,Dmetrics}/overview.py`
- `face/metrics/features/dimorphism.py`, `radar_summary.py`, `summary_advice.py`

**Please upload these** if you want me to verify/refactor them too -- right now `services/report_builder.py` assumes their function signatures match exactly what `photo.py` called.

I also didn't have:
- Your previous `main.py`/entry point or any config module, so `main.py` and `config.py` here are new, not adaptations.
- Any existing payment/Tribute integration code, so the payment flow in `handlers/callbacks.py` + `handlers/payment.py` is a fresh implementation (see note below).
- A `help.py` handler was referenced in your directory tree screenshot but not uploaded -- not included here.

## 6. Payment / Tribute note (read before deploying)

Tribute is typically an **external checkout page** (a Telegram Mini App / deep link), not a standard Telegram Bot Payments provider -- it doesn't plug into `pre_checkout_query` / `successful_payment` the way a provider token does. I implemented two paths:

1. **If `TRIBUTE_PAY_URL` is set**: the payment button links out to that URL. Crediting the user's balance afterward requires a **webhook from Tribute** into your bot's server confirming the payment -- I don't have Tribute's webhook payload/signature format, so that endpoint isn't built. You'll need their API docs to add a small `aiohttp`/FastAPI route that calls `UserRepository.add_balance()` on a verified webhook.
2. **Fallback (no Tribute URL configured)**: a native Telegram invoice, using Telegram Stars (`XTR`) by default, or fiat via `PAYMENT_PROVIDER_TOKEN` if you have a real Bot Payments provider. This path is fully wired end-to-end (`pre_checkout_query` -> `successful_payment` -> balance credited) and works today with no extra setup beyond a bot token.

## 7. Behavior notes worth knowing

- Balance is deducted **after** the quality gate passes, not before -- matches your spec exactly.
- If PDF generation or AI analysis throws after the balance was deducted, it's automatically refunded (`UserRepository.refund_one`).
- `try_deduct_one()` uses a conditional SQL `UPDATE ... WHERE balance > 0`, so two concurrent requests from the same user can't both succeed against a balance of 1.
- Logging is now milestone-only, in English, matching the format you asked for (`[INFO] User 12345 started processing.`, etc.) -- see `handlers/photo.py` and `database/repository.py`.
- `ai_analyzer.py`'s prompt no longer demands exact character counts (e.g. "MUST be 1800-2400 characters"); it now gives word-count *targets* framed as guidelines, since the page CSS already auto-scales font size to content length. Structural constraints that map to fixed template regions (exact bullet counts, exact paragraph counts) were kept, since those aren't arbitrary -- the template has that many slots.
