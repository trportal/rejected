import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ============================================
# CONFIGURATION - Edit these values
# ============================================

# NEVER hardcode this. Set it as an env var instead:
#   export BOT_TOKEN="123456:ABC..."
BOT_TOKEN = os.environ["BOT_TOKEN"]

#
# Each channel needs:
#   "label"   - display name for the button
#   "chat_id" - what get_chat_member() checks membership against.
#               For PUBLIC channels this is the @username.
#               For PRIVATE channels (invite-link only, like your 4th one),
#               @username does NOT exist, so you MUST put the numeric chat ID
#               here instead (looks like -1001234567890). See note below on
#               how to find it.
#   "join_url" - the actual link the button opens when tapped.
#
CHANNELS = [
    {"label": "Wechatted", "chat_id": "@wechatted", "join_url": "https://t.me/wechatted"},
    {
        "label": "Private Channel 1",
        # Invite-link only, no @username — verification uses the numeric ID.
        "chat_id": "-1003313300495",
        "join_url": "https://t.me/+m4qeH8h3UH05ZGY1",
    },
    {
        "label": "Private Channel 2",
        # Invite-link only, no @username — verification uses the numeric ID.
        "chat_id": "-1004346235911",
        "join_url": "https://t.me/+O9yHNTDOZXJiNDE1",
    },
]

WELCOME_MESSAGE = (
    "<b>🚫 ACCESS RESTRICTED</b>\n"
    "<code>▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬</code>\n\n"
    "You're <b>almost in</b> — the full guide is waiting.\n\n"
    "<blockquote><b>How to unlock it</b>\n"
    "🔹 Join <b>every</b> channel below\n"
    "🔹 Tap <b>🔓 Verify</b>\n"
    "🔹 Guide drops straight into your DMs</blockquote>\n"
    "🚨 <i>Leaving a channel after verifying will revoke access.</i>\n\n"
    "<code>▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬</code>\n"
    "<i>Tap a channel to join, then hit Verify.</i>"
)

SUCCESS_MESSAGE = (
    "<b>🚀 YOU'RE IN</b>\n"
    "<code>▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬</code>\n\n"
    "All channels confirmed ✔️\n"
    "Guide incoming — check your DMs 📬\n\n"
    "<code>▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬</code>\n"
    "<i>Thanks for joining!</i>"
)

NOT_JOINED_MESSAGE = (
    "🚫 Not yet — you're missing at least one channel.\n"
    "Join every channel listed, then hit Verify again."
)

ERROR_MESSAGE = "⚠️ Something broke on our end. Give it a few seconds and try again."

GUIDE_LINK = "https://t.me/etcservices/19"
GUIDE_CAPTION = (
    "<b>🎁 YOUR GUIDE IS READY</b>\n"
    "<code>▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬</code>\n\n"
    "Tap below to open it. Enjoy! 🔥"
)

# ============================================
# LOGGING SETUP
# ============================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============================================
# UI HELPERS
# ============================================

# Telegram's Bot API has no button-color parameter — inline keyboard buttons
# are always the client's default gray/blue. The closest thing to "colored"
# buttons is prefixing labels with colored emoji circles, done below.
CHANNEL_DOTS = ["🟦", "🟩", "🟪", "🟧", "🟥", "🟨"]  # cycles if you add more channels


def build_keyboard(show_retry: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            f"{CHANNEL_DOTS[i % len(CHANNEL_DOTS)]} {i + 1}. Join {ch['label']}",
            url=ch["join_url"],
        )]
        for i, ch in enumerate(CHANNELS)
    ]
    label = "♻️ VERIFY AGAIN" if show_retry else "🔓 VERIFY NOW"
    rows.append([InlineKeyboardButton(label, callback_data="verify")])
    return InlineKeyboardMarkup(rows)


# ============================================
# HANDLERS
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=build_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    try:
        not_joined = []
        for ch in CHANNELS:
            member = await context.bot.get_chat_member(chat_id=ch["chat_id"], user_id=user_id)
            if member.status not in ("member", "administrator", "creator"):
                not_joined.append(ch["label"])

        if not not_joined:
            # A callback query can only be answered once. Answer here,
            # on the branch that actually needs it.
            await query.answer()
            await query.edit_message_text(SUCCESS_MESSAGE, parse_mode=ParseMode.HTML)

            link_keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔥 OPEN GUIDE", url=GUIDE_LINK)]]
            )
            await context.bot.send_message(
                chat_id=user_id,
                text=GUIDE_CAPTION,
                reply_markup=link_keyboard,
                parse_mode=ParseMode.HTML,
            )
        else:
            # Answer with the alert FIRST — this is the callback's one answer.
            await query.answer(NOT_JOINED_MESSAGE, show_alert=True)
            # Then refresh the message so unjoined channels are still
            # clickable, and swap the button to "Verify Again" for clarity.
            await query.edit_message_text(
                WELCOME_MESSAGE,
                reply_markup=build_keyboard(show_retry=True),
                parse_mode=ParseMode.HTML,
            )

    except Exception as e:
        logger.error(f"Error during verification: {e}")
        try:
            await query.answer(ERROR_MESSAGE, show_alert=True)
        except Exception:
            pass  # query was already answered before the failure — nothing more we can do


# ============================================
# MAIN
# ============================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(verify, pattern="verify"))

    print("Bot is starting...")
    app.run_polling()


if __name__ == "__main__":
    main()