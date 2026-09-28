"""All user-facing strings live here."""

WELCOME = (
    "<b>Welcome to bp_guide AI</b> \n\n"
    "Face Aura mathematically evaluates the harmony of your facial features "
    "using 98 biometric measurements, comparing them against established "
    "aesthetic and anthropometric canons.\n\n"
    "Take a look at a sample report below 👇"
)

BALANCE_LINE = "💳 Your balance: <b>{balance}</b> analys{is_or_es}"
TODAY_STAT_LINE = "📈 Today users performed: <b>{count}</b> analyses"

# Заміни старий ANALYSIS_DETAILS на цей:
ANALYSIS_DETAILS = (
    "📍 Main menu › <b>Get Analysis</b>\n\n"
    "⚜️ <b>Transform Your Look with a Personalized Action Plan:</b>\n"
    "<blockquote><b>• True facial harmony</b> isn't guesswork—it's based on <b>objective biometrics</b>.\n"
    "<b>• Our AI</b> goes far beyond a basic score to deliver a personalized roadmap designed to <b>maximize your attractiveness</b> and upgrade your presence.\n"
    "<b>• bp_guide AI</b> identifies your key structural strengths and pinpoint areas for growth.\n"
    "<b>• You get</b> a targeted <b>Action Plan</b> packed with tailored grooming, styling, and practical steps to instantly <b>level up</b> how people perceive you.</blockquote>\n\n"
    "🚀 <b>Proven Results:</b>\n"
    "<blockquote><b>Hundreds of men</b> have already transformed their appearance and confidence using their custom action plan. <b>Join them</b> and start making the best impression possible.</blockquote>\n\n"
    "🔬 <b>High-Precision Facial Analysis:</b>\n"
    "Our advanced processing pipeline cancels out lens distortion and subtle head tilts for maximum geometric accuracy:\n"
    "<blockquote><b>• Quality Check:</b> Screens for proper lighting and head pose.\n"
    "<b>• 3D Frontalization:</b> Corrects perspective distortion.\n"
    "<b>• TTA:</b> Eliminates measurement bias using mirrored frames.</blockquote>\n\n"
    "💳 <b>Pricing:</b>\n"
    "{pricing_block}"
)

# Додай ці два нові рядки нижче:
PRICING_BLOCK_NORMAL = (
    "• 1 Full Analysis — <b>$4.29</b>\n"
    "• 3 Full Analyses — <b>$8.99</b>"
)

MAIN_MENU_PROMO_BEFORE = "🎁 <i>Complete a Free Ratio Analysis to unlock a 30% discount!</i>"
MAIN_MENU_PROMO_ACTIVE = "🔥 <b>30% OFF</b> on Full Analysis! Ends in: <b>{mins}m {secs}s</b>"

PRICING_BLOCK_DISCOUNT = (
    "• 1 Full Analysis — <del>$4.29</del> <b>$2.89</b> (🔥 30% OFF - {mins}m {secs}s left)\n"
    "• 3 Full Analyses — <b>$8.99</b>"
)

PAYMENT_SCREEN = (
    "📍 Main menu › Get Analysis › <b>Payment</b>\n\n"
    "<blockquote>⚜️ <b>Plan:</b> {count} Full Analys{is_or_es}\n"
    "💰 <b>Total to pay:</b> ${price}</blockquote>\n\n"
    "{discount_block}"
    "➤ <b>Payment Instructions:</b>\n\n"
    "<blockquote>💳 <b>Cards:</b> You can securely pay with a bank card from any country.\n"
    "⚡ <b>Instant delivery:</b> After payment, the analyses are credited automatically. Just send a photo to this chat to start!\n"
    "🎧 <b>Support:</b> If something goes wrong, you can always contact our support via the main menu.</blockquote>"
)

PAYMENT_DISCOUNT_BLOCK = (
    "🔥 <b>Your unlimited discount is active for {mins}m {secs}s more!</b>\n\n"
    "<blockquote>"
    "• Pay EXACTLY <b>$2.89</b> via the <b>'Pay by donation'</b> button below to receive 1 Full Analysis instead of $4.29.\n\n"
    "• If you don't want or you can't pay with discount using donation, text our admin <b>@mbilozir22</b> and he will send you a link to pay. After you pay, he will manually give you the analysis!\n\n"
    "<i>⚠️ Automatic Discount is ONLY valid via the 'Pay by donation' button. Paying via standard Card/SBP links will process the full $4.29 price if you use them now.</i>" 
    "</blockquote>\n\n"
)
DISCOUNT_EXPIRED_MSG = (
    "⏰ Your special discount offer has expired.\n"
    "If you still want to take advantage of it, please contact our support admin: {support}"
)

DISCOUNT_10M_WARNING = (
    "⏳ <b>Only 10 minutes left!</b>\n\n"
    "You have 10 minutes left to find out your true potential and get an objective evaluation "
    "with a <b>30% discount</b>.\n\n"
    "Tap the button below to get your Full Analysis now 👇"
)

NEED_BALANCE = (
    "You don't have any analyses left.\n"
    "Get one below to continue."
)

MANUAL_PAYMENT_SCREEN = (
    "📍 Main menu › Get Analysis › <b>Alternative payment</b>\n\n"
    "{discount_timer_block}"
    "You can easily pay using our direct donation system. The process is fully automated:\n\n"
    "<blockquote>1️⃣ Tap \"Donate to pay\" below.\n"
    "2️⃣ Enter exactly <b>{amount}</b> as the donation amount.\n"
    "3️⃣ Once the transaction is complete, the bot will instantly and automatically credit the analyses to your account!\n"
    "⚠️ Important when paying via Tribute: Do NOT check the 'Pay anonymously' box during checkout!</blockquote>\n\n"
    "If you'd like to pay using a different method or experience any issues, please contact our support directly: @mbilozir22"
)

STATUS_STEPS = [
    "🔍 Checking photo quality (lighting, pose)...",
    "📐 Calculating facial metrics...",
    "🧠 AI is analyzing your facial geometry...",
    "📄 Generating your personalized PDF report...",
    "✅ Done!",
]

REPORT_CAPTION = (
    "✅ <b>Face Analysis Complete</b>\n"
    "<i>Open the attached PDF below to see your full visual breakdown!</i>\n\n"
    "📄 <b>How to read your report:</b>\n"
    "<blockquote>1️⃣ Start with the <b>Overall Score</b> to understand your baseline.\n"
    "2️⃣ Review the <b>Radar Chart</b> to easily spot your strongest features and asymmetries.\n"
    "3️⃣ Read the entire <b>Metrics block</b> to understand the reasoning behind your score.\n"
    "4️⃣ Get advice on the <b>Style &amp; grooming advisory</b> page.\n"
    "5️⃣ Understand your <b>weak points</b> and maximize your appearance using the strategies in the file.</blockquote>\n\n"
    "🎁 <b>Bonus to your analysis:</b>\n\n"
    "<tg-spoiler>🎭 <b>Best Actor Match:</b> {actor_name}\n"
    "💡 <i>Tip: {actor_advice}</i>\n\n"
    "📚 <b>Biometric Studies for you:</b>\n"
    "{study_links}\n\n</tg-spoiler>"
    "<i>{quality_line}</i>"
)

PAYMENT_SUCCESS = (
    "🎉 <b>Payment successful!</b>\n\n"
    "Your total balance is now <b>{balance}</b> analys{is_or_es}.\n\n"
    "📸 <b>How to take the perfect photo(like in the example of full analysis):</b>\n"
    "• <b>Camera:</b> Ask a friend to take your picture using the main (rear) camera, or take a photo at arm's length. Set zoom to <b>x2</b> to prevent face distortion.\n"
    "• <b>Position:</b> Keep the camera <b>exactly at eye level</b> and look straight into the lens.\n"
    "• <b>Lighting:</b> Face a bright, even light source directly (like a window). Avoid harsh shadows on one side of your face.\n\n"
    "💡 <i>Tip: Our AI is very strict to ensure mathematical accuracy. If your photos keep getting rejected, simply move to a brighter location. If the system rejects all your attempts, don't worry — you can always skip the check after 3 bad attepts or contact our support!</i>\n\n"
    "Send your photo below to begin 👇"
)

QUALITY_LINE_ON = "Capture Quality: Optimal"
QUALITY_LINE_OFF = "Capture Quality: Check skipped"

GENERIC_ERROR = "An error occurred during processing. Please try again."
PHOTO_TOO_LARGE = "📦 Photo is too large (max 5 MB)."
CANNOT_READ_PHOTO = "❌ Cannot read the photo. Try another one."
LOW_RESOLUTION = (
    "⚠️ <b>Photo quality is too low.</b>\n"
    "Please upload an image with a resolution of at least {min_dim}x{min_dim} pixels."
)
BAD_ASPECT_RATIO = "⚠️ Photo has incorrect proportions or invalid dimensions."
NO_FACE_DETECTED = "❌ Face is too far away or not detected. Please look directly into the lens."
CROP_FAILED = "❌ Failed to crop image for PDF generation."
TTA_FAILED = "👤 Analysis pipeline failed on this photo. Please try another one."
BUSY_PROCESSING = "⏳ Your previous photo is currently being analyzed. Please wait a moment..."

QUALITY_GATE_REJECTED_HEADER = (
    "❌ <b>Photo Rejected by Quality Gate</b>\n\n"
    "To ensure mathematical accuracy of facial symmetry, capture conditions must be strict.\n\n"
    "<b>Please fix the following issues:</b>\n"
)
QUALITY_GATE_TIP = (
    "ℹ️ <i>Tip: Ask a friend to take your picture using the main (rear) camera, or use a tripod. "
    "Set zoom to x2, keep the camera exactly at eye level, and face a bright, even light source directly.</i>"
)

SKIP_QUALITY_CHECK_MSG = (
    "😅 <b>Having trouble getting the photo approved?</b>\n\n"
    "Our quality check is highly strict to guarantee the most accurate comprehensive biometric analysis. "
    "However, if you are confident that your photo is clear, perfectly lit, and distortion-free, "
    "You can choose to skip this check. While it may slightly affect accuracy, the impact will be minimal thanks to our 3D map and TTA system..\n\n"
    "<i>(If you're not sure, just ignore this message and keep sending new photos until our system approves one! "
    "If it still doesn't work, try moving to a brighter location or contact Support)</i>"
)

SKIP_CHECK_CONFIRMED = "✅ <b>Quality check disabled for your next photo.</b> Please upload it now."

# --- Buttons ---
BTN_GET_ANALYSIS = "💎 Get Full Face Analysis"
BTN_GET_FULL_ANALYSIS_1 = "🧠 Get 1 Full Analysis ($4.29)"
BTN_GET_FULL_ANALYSIS_3 = "💎 Get 3 Full Analyses ($8.99)"
BTN_PAY = "💳 Pay by card / SBP"
BTN_PAY_CARD = "💳 Pay by card / SBP"
BTN_PAY_STARS = "⭐ Pay with Telegram Stars"
BTN_CANT_PAY = "🔥 Pay by donation"
BTN_DONATE = "💳 Donate to pay"
BTN_CONTACT_SUPPORT = "🎧 Contact support"
BTN_BACK = "⬅️ Back"
BTN_SKIP_CHECK = "⚠️ Yes, I'm confident. Skip check."


# --- Helper Functions ---
def balance_line(balance: int) -> str:
    return BALANCE_LINE.format(balance=balance, is_or_es="is" if balance == 1 else "es")

def payment_success(balance: int) -> str:
    return PAYMENT_SUCCESS.format(balance=balance, is_or_es="is" if balance == 1 else "es")