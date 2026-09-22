import random
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import config
import db
import texts
import keyboards
from services import razorpay_service

log = logging.getLogger("crevio.deposit")


async def method_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.split(":")[2]  # INR | TRX
    await query.edit_message_text(
        texts.DEPOSIT_PICK_AMOUNT, reply_markup=keyboards.deposit_amount_kb(method)
    )


async def preset_amount_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, _, method, amount_str = query.data.split(":")
    amount = float(amount_str)
    await _create_and_show(query, context, method, amount)


async def custom_amount_requested(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.split(":")[2]
    context.user_data["awaiting"] = ("deposit_custom", method)
    prompt = texts.DEPOSIT_CUSTOM_ASK_INR if method == "INR" else texts.DEPOSIT_CUSTOM_ASK_TRX
    await query.edit_message_text(prompt)


async def handle_custom_amount_text(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
    text = update.message.text.strip().replace(",", "")
    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text(texts.DEPOSIT_INVALID_NUMBER)
        return

    min_amount = config.MIN_DEPOSIT_INR if method == "INR" else config.MIN_DEPOSIT_TRX
    if amount < min_amount:
        err = texts.DEPOSIT_MIN_ERROR_INR if method == "INR" else texts.DEPOSIT_MIN_ERROR_TRX
        await update.message.reply_text(err)
        return

    context.user_data.pop("awaiting", None)
    await _create_and_show_message(update.message, context, method, amount)


async def _create_and_show(query, context, method: str, amount: float):
    await _create_and_show_message(query.message, context, method, amount, edit=query)


async def _create_and_show_message(message, context, method: str, amount: float, edit=None):
    user_id = message.chat_id if hasattr(message, "chat_id") else message.chat.id

    if method == "INR":
        deposit_id = db.create_pending_deposit(user_id, "INR", amount)
        try:
            link = razorpay_service.create_payment_link(user_id, deposit_id, amount)
        except Exception as e:
            log.error("Razorpay link creation failed: %s", e)
            await message.reply_text(texts.GENERIC_ERROR)
            return

        text = texts.DEPOSIT_DETAILS_INR.format(amount=amount, minutes=config.DEPOSIT_TIMEOUT_MIN)
        kb = keyboards.pay_now_kb(link["short_url"])
    else:
        unique_amount = _generate_unique_trx_amount(amount)
        db.create_pending_deposit(user_id, "TRX", unique_amount)
        text = texts.DEPOSIT_DETAILS_TRX.format(
            amount=unique_amount, wallet=config.TRX_WALLET_ADDRESS, minutes=config.DEPOSIT_TIMEOUT_MIN
        )
        kb = keyboards.back_to_menu_kb()

    if edit:
        await edit.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


def _generate_unique_trx_amount(base_amount: float) -> float:
    """Adds a small random fractional offset so each pending TRX deposit has a
    one-of-a-kind amount, letting the cron job match an incoming payment to
    the right user by amount alone."""
    active = {round(r["requested_amount"], 4) for r in db.get_active_trx_pending_amounts()}
    for _ in range(50):
        offset = round(random.uniform(0.0001, 0.0999), 4)
        candidate = round(base_amount + offset, 4)
        if candidate not in active:
            return candidate
    return round(base_amount + random.uniform(0.0001, 0.0999), 4)
