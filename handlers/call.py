import re
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import config
import db
import texts
import keyboards
from utils import is_valid_india_number, fmt, max_call_minutes
from services import edesy

log = logging.getLogger("crevio.call")


def _normalize_own_number(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("91") and len(digits) == 12:
        return "+" + digits
    if len(digits) == 10:
        return "+91" + digits
    return "+" + digits


async def start_call_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, row: dict):
    query = update.callback_query

    if row.get("active_call_id"):
        await query.answer(texts.CALL_ALREADY_ACTIVE, show_alert=True)
        return

    if not row.get("phone_number"):
        await query.answer()
        kb = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Share My Number", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True,
        )
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="📱 We need your own number once, so we can ring <b>you</b> first before connecting your call.",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
        return

    await query.answer()
    context.user_data["awaiting"] = ("call_number",)
    await context.bot.send_message(chat_id=query.from_user.id, text=texts.CALL_ASK_NUMBER, parse_mode=ParseMode.HTML)


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if contact.user_id != update.effective_user.id:
        return  # ignore contacts shared that aren't the user's own
    phone = _normalize_own_number(contact.phone_number)
    db.set_phone_number(update.effective_user.id, phone)
    await update.message.reply_text("✅ Number saved!", reply_markup=ReplyKeyboardRemove())

    context.user_data["awaiting"] = ("call_number",)
    await update.message.reply_text(texts.CALL_ASK_NUMBER, parse_mode=ParseMode.HTML)


async def handle_call_number_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    # Auto-normalize: if user types 10-digit or 91+10-digit, convert to +91XXXXXXXXXX
    number = _normalize_own_number(raw)
    if not is_valid_india_number(number):
        await update.message.reply_text(texts.CALL_INVALID_NUMBER)
        return

    context.user_data.pop("awaiting", None)
    row = db.get_user(update.effective_user.id)
    balance = float(row["balance"])
    min_needed = config.MIN_CALL_START_BALANCE_MIN * config.CALL_RATE_PER_MIN

    if balance < min_needed:
        await update.message.reply_text(
            texts.CALL_INSUFFICIENT_BALANCE.format(
                min_minutes=config.MIN_CALL_START_BALANCE_MIN,
                balance=fmt(balance),
                currency=config.BOT_CURRENCY,
                rate=config.CALL_RATE_PER_MIN,
            ),
            parse_mode=ParseMode.HTML,
        )
        return

    context.user_data["pending_call_number"] = number
    max_minutes = max_call_minutes(balance, config.CALL_RATE_PER_MIN)
    text = texts.CALL_CONFIRM.format(
        number=number, rate=config.CALL_RATE_PER_MIN, currency=config.BOT_CURRENCY,
        balance=fmt(balance), max_minutes=max_minutes,
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboards.call_confirm_kb())


async def call_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    row = db.get_user(user_id)

    if row.get("active_call_id"):
        await query.answer(texts.CALL_ALREADY_ACTIVE, show_alert=True)
        return

    number = context.user_data.pop("pending_call_number", None)
    if not number:
        await query.answer()
        await query.edit_message_text(texts.GENERIC_ERROR)
        return

    balance = float(row["balance"])
    min_needed = config.MIN_CALL_START_BALANCE_MIN * config.CALL_RATE_PER_MIN
    if balance < min_needed:
        await query.answer()
        await query.edit_message_text(
            texts.CALL_INSUFFICIENT_BALANCE.format(
                min_minutes=config.MIN_CALL_START_BALANCE_MIN,
                balance=fmt(balance), currency=config.BOT_CURRENCY, rate=config.CALL_RATE_PER_MIN,
            ),
            parse_mode=ParseMode.HTML,
        )
        return

    await query.answer()
    await query.edit_message_text(texts.CALL_STARTING)

    call_id = db.create_call(user_id, number, via_api=False)
    db.set_active_call(user_id, call_id)

    try:
        result = edesy.initiate_masked_call(row["phone_number"], number)
        edesy_call_id = result.get("call_id") or result.get("id")  # adjust to Edesy's real field name
        db.set_call_edesy_id(call_id, edesy_call_id)
    except Exception as e:
        log.error("Edesy call initiation failed: %s", e)
        db.end_call(call_id, "failed", 0, 0)
        db.set_active_call(user_id, None)
        await context.bot.send_message(chat_id=user_id, text=texts.CALL_FAILED)
