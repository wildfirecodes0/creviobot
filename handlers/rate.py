from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import config
import db
import texts
import keyboards

STAR_MAP = {
    5: "❤️❤️❤️❤️❤️",
    4: "🤎🤎🤎🤎",
    3: "💜💜💜",
    2: "💙💙",
    1: "🖤",
}


async def rate_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "rate:open":
        await query.answer()
        await query.edit_message_text(
            texts.RATE_US_PROMPT, parse_mode=ParseMode.HTML, reply_markup=keyboards.rate_us_kb()
        )
        return

    stars = int(data.split(":")[1])
    user = query.from_user
    row = db.get_user(user.id)
    if row is None:
        row = db.create_user_if_missing(user.id, user.first_name or "Friend", user.username)

    if row.get("has_rated"):
        await query.answer(texts.RATE_US_ALREADY, show_alert=True)
        return

    if stars in (1, 2, 3):
        # Per spec: 1-3 hearts do nothing, no popup, not marked as rated
        # (so the user can still rate 4-5 later and have it count).
        await query.answer()
        return

    # 4 or 5 hearts
    db.mark_rated(user.id)
    await query.answer(texts.RATE_US_THANKS, show_alert=True)

    broadcast = texts.RATING_BROADCAST.format(
        first_name=user.first_name or "Someone",
        stars=STAR_MAP[stars],
        num_stars=stars,
        channel=config.RATING_CHANNEL_USERNAME,
    )
    try:
        await context.bot.send_message(
            chat_id=config.RATING_CHANNEL_USERNAME, text=broadcast, parse_mode=ParseMode.HTML
        )
    except Exception:
        pass  # bot might not be admin in that channel yet — doesn't block the user's flow
