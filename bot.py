import json
import asyncio
import logging
import threading

from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ChatMemberHandler, filters,
)

import config
import db
import texts
from handlers import general, rate, deposit, apikey, call as call_handlers
from handlers.text_router import route_text
from services import razorpay_service, tron, billing
from services.public_api import public_api_bp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("crevio.bot")

# ---------------------------------------------------------------------------
# Telegram Application (python-telegram-bot)
# ---------------------------------------------------------------------------

telegram_app = Application.builder().token(config.BOT_TOKEN).build()

telegram_app.add_handler(CommandHandler("start", general.start_cmd))
telegram_app.add_handler(ChatMemberHandler(general.chat_member_update, ChatMemberHandler.CHAT_MEMBER))

# Rate Us (must come before the generic menu router since both use callback_data)
telegram_app.add_handler(CallbackQueryHandler(rate.rate_router, pattern=r"^rate:"))

# Deposit flows
telegram_app.add_handler(CallbackQueryHandler(deposit.method_chosen, pattern=r"^dep:method:"))
telegram_app.add_handler(CallbackQueryHandler(deposit.preset_amount_chosen, pattern=r"^dep:amt:"))
telegram_app.add_handler(CallbackQueryHandler(deposit.custom_amount_requested, pattern=r"^dep:custom:"))

# Call flow
telegram_app.add_handler(CallbackQueryHandler(call_handlers.call_start_callback, pattern=r"^call:start$"))
telegram_app.add_handler(MessageHandler(filters.CONTACT, call_handlers.handle_contact))

# History detail view
telegram_app.add_handler(CallbackQueryHandler(general.history_view, pattern=r"^hist:view:"))

# Everything else that starts with "menu:"
telegram_app.add_handler(CallbackQueryHandler(general.menu_router, pattern=r"^menu:"))

# Free-text input (custom deposit amount, phone number for a call)
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text))


# ---------------------------------------------------------------------------
# Background asyncio loop — lets our sync Flask routes and sync APScheduler
# jobs safely call into python-telegram-bot's async Application.
# ---------------------------------------------------------------------------

_loop = asyncio.new_event_loop()


def _run_loop():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


threading.Thread(target=_run_loop, daemon=True).start()


def run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, _loop)


run_async(telegram_app.initialize()).result()
run_async(telegram_app.bot.set_webhook(
    url=f"{config.WEBHOOK_BASE_URL}/telegram-webhook/{config.TELEGRAM_WEBHOOK_SECRET}"
)).result()

log.info("Telegram webhook set.")


# ---------------------------------------------------------------------------
# Flask app — this is the single port Render sees.
# ---------------------------------------------------------------------------

flask_app = Flask(__name__)
flask_app.register_blueprint(public_api_bp)


@flask_app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "crevio-bot"}), 200


@flask_app.route(f"/telegram-webhook/{config.TELEGRAM_WEBHOOK_SECRET}", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)
    if not data:
        return "Bad Request", 400
    try:
        update = Update.de_json(data, telegram_app.bot)
        run_async(telegram_app.process_update(update))
    except Exception as e:
        log.exception("Error processing Telegram update: %s", e)
    return "OK", 200


@flask_app.route("/razorpay-webhook", methods=["POST"])
def razorpay_webhook():
    signature = request.headers.get("X-Razorpay-Signature", "")
    raw_body = request.get_data()

    if not razorpay_service.verify_webhook_signature(raw_body, signature):
        log.warning("Razorpay webhook signature mismatch.")
        return jsonify({"error": "invalid signature"}), 400

    payload = json.loads(raw_body)
    event = payload.get("event", "")

    if event == "payment_link.paid":
        entity = payload["payload"]["payment_link"]["entity"]
        reference_id = entity.get("reference_id", "")  # "dep_<deposit_id>"
        notes = entity.get("notes", {})
        amount_paid = entity.get("amount_paid", 0) / 100.0

        try:
            deposit_id = int(reference_id.replace("dep_", ""))
        except (ValueError, AttributeError):
            return jsonify({"status": "ignored"}), 200

        telegram_id = notes.get("telegram_id")
        run_async(_credit_inr_deposit(deposit_id, telegram_id, amount_paid))

    return jsonify({"status": "ok"}), 200


async def _credit_inr_deposit(deposit_id: int, telegram_id: str, amount_paid: float):
    rows = db._run("SELECT * FROM pending_deposits WHERE id = ? AND status = 'pending'", [deposit_id])
    if not rows:
        return  # already processed, or expired — silently ignore per spec
    pending = rows[0]

    # Exact-amount match only — anything else is silently ignored, never credited.
    if abs(float(pending["requested_amount"]) - amount_paid) > 0.0001:
        log.warning("INR deposit %s amount mismatch: expected %s got %s",
                    deposit_id, pending["requested_amount"], amount_paid)
        return

    # Prefer telegram_id from DB record (more reliable than webhook notes)
    try:
        tid = int(telegram_id) if telegram_id else int(pending["telegram_id"])
    except (ValueError, TypeError):
        tid = int(pending["telegram_id"])

    db.mark_deposit_paid(deposit_id)
    db.add_balance(tid, amount_paid)
    db.add_transaction(tid, "deposit", amount_paid, "INR", "success", {})

    try:
        await telegram_app.bot.send_message(
            chat_id=tid,
            text=f"✅ Deposit of <b>{amount_paid:.2f} {config.BOT_CURRENCY}</b> received! Your balance has been updated.",
            parse_mode="HTML",
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Background schedulers: live call billing (5s) + TRX payment matching + deposit expiry
# ---------------------------------------------------------------------------

def _billing_tick():
    run_async(billing.process_ongoing_calls(telegram_app.bot))


def _trx_check_tick():
    try:
        transfers = tron.get_recent_incoming_transfers(limit=50)
        pending = db.get_active_trx_pending_amounts()
        if not pending or not transfers:
            return

        for p in pending:
            target = round(float(p["requested_amount"]), 4)
            match = next((t for t in transfers if round(t["amount_trx"], 4) == target), None)
            if match:
                run_async(_credit_trx_deposit(p["id"], p["telegram_id"], target))
    except Exception as e:
        log.exception("TRX check tick failed: %s", e)


async def _credit_trx_deposit(deposit_id: int, telegram_id: int, trx_amount: float):
    rows = db._run("SELECT * FROM pending_deposits WHERE id = ? AND status = 'pending'", [deposit_id])
    if not rows:
        return
    db.mark_deposit_paid(deposit_id)
    currency_amount = trx_amount * config.TRX_TO_CURRENCY_RATE
    db.add_balance(telegram_id, currency_amount)
    db.add_transaction(telegram_id, "deposit", currency_amount, "TRX", "success", {"trx_amount": trx_amount})

    try:
        await telegram_app.bot.send_message(
            chat_id=telegram_id,
            text=f"✅ Deposit of <b>{trx_amount} TRX</b> received! "
                 f"<b>{currency_amount:.2f} {config.BOT_CURRENCY}</b> added to your balance.",
            parse_mode="HTML",
        )
    except Exception:
        pass


def _expire_deposits_tick():
    try:
        db.expire_old_deposits()
    except Exception as e:
        log.exception("Deposit expiry tick failed: %s", e)


scheduler = BackgroundScheduler()
scheduler.add_job(_billing_tick, "interval", seconds=config.BILLING_TICK_SECONDS, max_instances=1)
scheduler.add_job(_trx_check_tick, "interval", seconds=20, max_instances=1)
scheduler.add_job(_expire_deposits_tick, "interval", minutes=1, max_instances=1)
scheduler.start()


if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=config.PORT, threaded=True)
