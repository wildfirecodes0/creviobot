"""
Runs on a 5-second tick (see bot.py's scheduler setup) and is the single
source of truth for charging users while a call is live. Whether the call
was started from inside the bot or via the public API, it always goes
through db.create_call(), so this one loop bills both the same way.

BILLING RULE: Ceiling-per-minute billing.
  2 min 1 sec  → charged as 3 full minutes
  1 min 0 sec  → charged as 1 full minute
  0 min 30 sec → charged as 1 full minute (minimum 1 minute)

Assumption (flag for you to confirm against Edesy's real API): get_call_status()
returns a dict roughly like {"status": "ringing"|"in-progress"|"completed"|"failed",
"duration_seconds": int}. If Edesy's actual field names differ, only
services/edesy.py needs to change — this file just reads whatever
get_call_status() gives back via the two lines marked below.
"""
import math
import logging
from datetime import datetime, timezone
from telegram.constants import ParseMode

import config
import db
import texts
from services import edesy

log = logging.getLogger("crevio.billing")

RINGING_TIMEOUT_SEC = 60  # give up if never bridged within this long


def _billable_minutes(duration_seconds: int) -> int:
    """
    Ceiling billing: any started minute is charged in full.
    2 min 1 sec → 3, 1 min 0 sec → 1, 30 sec → 1, 0 sec → 0
    """
    if duration_seconds <= 0:
        return 0
    return math.ceil(duration_seconds / 60)


def _cost_for_seconds(duration_seconds: int) -> float:
    """Cost based on ceiling minutes."""
    return round(_billable_minutes(duration_seconds) * config.CALL_RATE_PER_MIN, 4)


async def process_ongoing_calls(bot):
    calls = db.get_ongoing_calls()
    for call in calls:
        try:
            await _process_one(bot, call)
        except Exception as e:
            log.exception("Billing tick failed for call %s: %s", call.get("id"), e)


async def _process_one(bot, call: dict):
    call_id = call["id"]
    telegram_id = call["telegram_id"]
    edesy_call_id = call.get("edesy_call_id")

    if not edesy_call_id:
        return  # not yet confirmed by Edesy, nothing to bill

    status_data = edesy.get_call_status(edesy_call_id)
    provider_status = status_data.get("status", "unknown")          # <- adjust if Edesy's field name differs
    duration_seconds = int(status_data.get("duration_seconds", 0))   # <- adjust if Edesy's field name differs

    if provider_status == "ringing":
        started = datetime.fromisoformat(call["started_at"])
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        if elapsed > RINGING_TIMEOUT_SEC:
            edesy.hangup_call(edesy_call_id)
            await _finalize(bot, call, 0, 0, status="failed", reason="ring_timeout")
        return  # no billing while it hasn't connected yet

    if provider_status in ("in-progress", "answered", "bridged"):
        new_cost = _cost_for_seconds(duration_seconds)
        delta = round(new_cost - float(call.get("cost") or 0), 4)

        user = db.get_user(telegram_id)
        if user is None:
            return

        if delta > 0 and float(user["balance"]) < delta:
            edesy.hangup_call(edesy_call_id)
            await _finalize(bot, call, duration_seconds, float(call.get("cost") or 0), status="completed",
                             reason="insufficient_balance")
            return

        if delta > 0:
            db.deduct_balance(telegram_id, delta)
        db.update_call_progress(call_id, duration_seconds, new_cost)
        return

    if provider_status in ("completed", "failed", "no-answer", "busy"):
        final_cost = _cost_for_seconds(duration_seconds)
        already_billed = float(call.get("cost") or 0)
        delta = round(final_cost - already_billed, 4)
        if delta > 0:
            user = db.get_user(telegram_id)
            if user and float(user["balance"]) >= delta:
                db.deduct_balance(telegram_id, delta)
            else:
                final_cost = already_billed  # can't bill more than what's left
        await _finalize(bot, call, duration_seconds, final_cost,
                         status="completed" if provider_status == "completed" else "failed")


async def _finalize(bot, call: dict, duration_seconds: int, final_cost: float, status: str, reason: str = None):
    call_id = call["id"]
    telegram_id = call["telegram_id"]
    billed_minutes = _billable_minutes(duration_seconds)
    actual_min = round(duration_seconds / 60, 1)  # for display only

    db.end_call(call_id, status, duration_seconds, final_cost)
    db.set_active_call(telegram_id, None)
    db.add_spent_and_minutes(telegram_id, final_cost, billed_minutes)

    ref_id = db.add_transaction(
        telegram_id, "call", final_cost, None, status,
        {
            "number": call["number"],
            "duration_actual_min": actual_min,
            "duration_billed_min": billed_minutes,
            "via_api": bool(call.get("via_api")),
        },
    )

    if call.get("via_api"):
        return  # API-triggered calls don't get a chat message — caller polls their own system

    user = db.get_user(telegram_id)
    balance = float(user["balance"]) if user else 0
    text = texts.CALL_ENDED.format(
        duration=actual_min,
        amount=f"{final_cost:.2f}",
        currency=config.BOT_CURRENCY,
        balance=f"{balance:.2f}",
    )
    try:
        await bot.send_message(chat_id=telegram_id, text=text, parse_mode=ParseMode.HTML)
    except Exception:
        pass
