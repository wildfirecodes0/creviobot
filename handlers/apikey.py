from telegram.constants import ParseMode

import config
import db
import texts
import keyboards
from utils import fmt


async def render_apikey(query, row: dict):
    balance = float(row["balance"])
    if balance < config.API_MIN_BALANCE:
        text = texts.API_LOCKED.format(
            min_balance=fmt(config.API_MIN_BALANCE),
            currency=config.BOT_CURRENCY,
            balance=fmt(balance),
        )
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboards.apikey_locked_kb())
        return

    api_key = row.get("api_key")
    if not api_key:
        api_key = db.gen_api_key()
        db.set_api_key(row["telegram_id"], api_key)

    endpoint = f"{config.WEBHOOK_BASE_URL}/api/v1/call"
    text = texts.API_UNLOCKED.format(endpoint=endpoint, api_key=api_key)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboards.back_to_menu_kb())
