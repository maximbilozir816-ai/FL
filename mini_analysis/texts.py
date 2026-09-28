"""All user-facing strings for the free mini-analysis feature.
Kept separate from texts/en.py so the main copy module stays untouched."""

BTN_FREE_MINI_ANALYSIS = "🎁 Get 1 Free ratio analysis"
BTN_SKIP_MINI_CHECK = "⚠️ Yes, I'm confident. Skip check."

NO_FREE_TRIES_LEFT = "You don't have any free ratio analyses left. Get a full analysis below to continue."

MINI_PHOTO_INSTRUCTIONS = (
    "🎁 <b>Free Ratio Analysis</b>\n\n"
    "<blockquote>⚡ <b>Special Offer:</b> You will get a <b>30% discount</b> for a full facial breakdown for <b>20 minutes</b> right after using your free attempt!</blockquote>\n\n"
    "This free preview measures a small set of facial ratios (eye spacing and nose "
    "proportions) to give you a quick glimpse into your facial geometry.\n\n"
    "<blockquote>📸 <b>How to take the photo:</b>\n"
    "• <b>Camera:</b> Use the main (rear) camera or take a photo at arm's length. Set zoom to <b>x2</b>.\n"
    "• <b>Position:</b> Keep the camera <b>exactly at eye level</b> and look straight into the lens.\n"
    "• <b>Lighting:</b> Face a bright, even light source directly. Avoid harsh shadows.</blockquote>\n\n"
    "<i>Note: The free mini-analysis does not include strict quality and pose checks. The Full Analysis rigorously verifies your photo to ensure the most accurate assessment.</i>\n\n"
    "Send your photo below to begin 👇"
)

MINI_STATUS_PROCESSING = "🔍 Analyzing your facial ratios..."

MINI_REPORT_CAPTION = (
    "⬆️ <b>Your Free Ratio Analysis is ready!</b>\n\n"
    "<blockquote>• This preview covers a small slice of what the full report measures.\n"
    "• The full analysis includes 18+ metrics, an AI-written breakdown, celebrity\n"
    "• archetype matches, and a complete grooming & styling action plan.</blockquote>\n\n"
    "🔥 <b>SPECIAL OFFER:</b> You have a <b>30% discount</b> on the Full Analysis for the next <b>20 minutes</b>!\n\n"
    "⬇️ Click the button below to claim it."
)

# Залишені порожніми для сумісності з імпортами в інших місцях, щоб нічого не зламалося
MINI_SKIP_CHECK_CONFIRMED = ""
MINI_OLD_BUTTON_NOTICE = ""
MINI_SKIP_QUALITY_CHECK_MSG = ""
MINI_SUCCESS_PASSED = ""
MINI_SUCCESS_SKIPPED = ""

def mini_tries_granted_notice(amount: int) -> str:
    plural = "analysis" if amount == 1 else "analyses"
    return f"🎁 <b>Our team gave you {amount} more mini {plural}.</b>"