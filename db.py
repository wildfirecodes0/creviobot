"""
Thin wrapper around Cloudflare D1's HTTP API, plus every query the bot needs.
D1 has no persistent connection — every call is one HTTPS request to
Cloudflare's REST endpoint.
"""
import json
import time
import random
import string
import logging
from datetime import datetime, timedelta, timezone

import requests

import config

log = logging.getLogger("crevio.db")

D1_URL = (
    f"https://api.cloudflare.com/client/v4/accounts/"
    f"{config.CF_ACCOUNT_ID}/d1/database/{config.CF_D1_DATABASE_ID}/query"
)
_HEADERS = {
    "Authorization": f"Bearer {config.CF_API_TOKEN}",
    "Content-Type": "application/json",
}


def _run(sql: str, params: list = None, retries: int = 3):
    """Execute one SQL statement against D1. Returns list of result rows (dicts)."""
    payload = {"sql": sql, "params": params or []}
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.post(D1_URL, headers=_HEADERS, json=payload, timeout=15)
            data = resp.json()
        except Exception as e:  # network hiccup, JSON decode failure, etc.
            last_err = e
            time.sleep(0.5 * (attempt + 1))
            continue

        if not data.get("success", False):
            errors = data.get("errors", [])
            # Check specifically for auth errors (code 10000) — these should not be retried
            if any(e.get("code") == 10000 for e in errors):
                log.error(
                    "D1 Authentication error — check CF_API_TOKEN and CF_ACCOUNT_ID env vars. "
                    "The token may be expired or have insufficient D1 permissions. "
                    "sql=%s | errors=%s", sql, errors
                )
                raise RuntimeError(
                    f"D1 Authentication failed (code 10000). "
                    f"Verify CF_API_TOKEN has 'D1 Edit' permission and is not expired. "
                    f"errors={errors}"
                )
            raise RuntimeError(f"D1 query failed: {errors} | sql={sql} | params={params}")

        result = data.get("result", [])
        if not result:
            return []
        return result[0].get("results", [])

    raise RuntimeError(f"D1 request failed after {retries} attempts: {last_err}")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def gen_ref_id() -> str:
    return "REF-CV" + "".join(random.choices(string.digits, k=5))


def gen_api_key() -> str:
    return "crv_live_" + "".join(
        random.choices(string.ascii_letters + string.digits, k=24)
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def get_user(telegram_id: int):
    rows = _run("SELECT * FROM users WHERE telegram_id = ?", [telegram_id])
    return rows[0] if rows else None


def create_user_if_missing(telegram_id: int, first_name: str, username: str, ref_by: int = None):
    existing = get_user(telegram_id)
    if existing:
        return existing
    _run(
        """INSERT INTO users
           (telegram_id, first_name, username, balance, total_spent, total_minutes,
            joined_channel, has_rated, ref_by, ref_count, ref_earning, api_key,
            active_call_id, joining_date)
           VALUES (?, ?, ?, 0, 0, 0, 0, 0, ?, 0, 0, NULL, NULL, ?)""",
        [telegram_id, first_name, username, ref_by, now_iso()],
    )
    return get_user(telegram_id)


def set_joined_channel(telegram_id: int, value: bool = True):
    _run("UPDATE users SET joined_channel = ? WHERE telegram_id = ?", [1 if value else 0, telegram_id])


def update_first_name_username(telegram_id: int, first_name: str, username: str):
    _run(
        "UPDATE users SET first_name = ?, username = ? WHERE telegram_id = ?",
        [first_name, username, telegram_id],
    )


def add_balance(telegram_id: int, amount: float):
    _run("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", [amount, telegram_id])


def deduct_balance(telegram_id: int, amount: float):
    _run("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", [amount, telegram_id])


def add_spent_and_minutes(telegram_id: int, amount: float, minutes: float):
    _run(
        "UPDATE users SET total_spent = total_spent + ?, total_minutes = total_minutes + ? WHERE telegram_id = ?",
        [amount, minutes, telegram_id],
    )


def mark_rated(telegram_id: int):
    _run("UPDATE users SET has_rated = 1 WHERE telegram_id = ?", [telegram_id])


def set_active_call(telegram_id: int, call_id):
    _run("UPDATE users SET active_call_id = ? WHERE telegram_id = ?", [call_id, telegram_id])


def set_phone_number(telegram_id: int, phone_number: str):
    _run("UPDATE users SET phone_number = ? WHERE telegram_id = ?", [phone_number, telegram_id])


def set_api_key(telegram_id: int, key: str):
    _run("UPDATE users SET api_key = ? WHERE telegram_id = ?", [key, telegram_id])


def get_user_by_api_key(api_key: str):
    rows = _run("SELECT * FROM users WHERE api_key = ?", [api_key])
    return rows[0] if rows else None


def increment_referral(ref_by_id: int, bonus: float):
    _run(
        "UPDATE users SET ref_count = ref_count + 1, ref_earning = ref_earning + ?, balance = balance + ? WHERE telegram_id = ?",
        [bonus, bonus, ref_by_id],
    )


# ---------------------------------------------------------------------------
# Transactions (unified history: calls + deposits)
# ---------------------------------------------------------------------------

def add_transaction(telegram_id: int, tx_type: str, amount: float, method: str,
                     status: str, detail: dict) -> str:
    ref_id = gen_ref_id()
    _run(
        """INSERT INTO transactions (ref_id, telegram_id, type, amount, method, status, detail_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [ref_id, telegram_id, tx_type, amount, method, status, json.dumps(detail), now_iso()],
    )
    return ref_id


def get_transactions_page(telegram_id: int, page: int, page_size: int):
    offset = (page - 1) * page_size
    rows = _run(
        "SELECT * FROM transactions WHERE telegram_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
        [telegram_id, page_size, offset],
    )
    total = _run("SELECT COUNT(*) as c FROM transactions WHERE telegram_id = ?", [telegram_id])
    total_count = total[0]["c"] if total else 0
    return rows, total_count


def get_transaction_by_ref(ref_id: str):
    rows = _run("SELECT * FROM transactions WHERE ref_id = ?", [ref_id])
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Pending deposits (INR + TRX)
# ---------------------------------------------------------------------------

def create_pending_deposit(telegram_id: int, method: str, requested_amount: float,
                            razorpay_order_id: str = None) -> int:
    created = datetime.now(timezone.utc)
    expires = created + timedelta(minutes=config.DEPOSIT_TIMEOUT_MIN)
    rows = _run(
        """INSERT INTO pending_deposits
           (telegram_id, method, requested_amount, razorpay_order_id, status, created_at, expires_at)
           VALUES (?, ?, ?, ?, 'pending', ?, ?) RETURNING id""",
        [telegram_id, method, requested_amount, razorpay_order_id,
         created.isoformat(), expires.isoformat()],
    )
    return rows[0]["id"] if rows else None


def get_pending_deposit_by_order(order_id: str):
    rows = _run(
        "SELECT * FROM pending_deposits WHERE razorpay_order_id = ? AND status = 'pending'",
        [order_id],
    )
    return rows[0] if rows else None


def get_active_trx_pending_amounts():
    """All amounts currently 'reserved' for pending, non-expired TRX deposits."""
    rows = _run(
        "SELECT requested_amount, telegram_id, id FROM pending_deposits "
        "WHERE method = 'TRX' AND status = 'pending' AND expires_at > ?",
        [now_iso()],
    )
    return rows


def mark_deposit_paid(deposit_id: int):
    _run("UPDATE pending_deposits SET status = 'paid' WHERE id = ?", [deposit_id])


def expire_old_deposits():
    _run(
        "UPDATE pending_deposits SET status = 'expired' WHERE status = 'pending' AND expires_at <= ?",
        [now_iso()],
    )


# ---------------------------------------------------------------------------
# Calls
# ---------------------------------------------------------------------------

def create_call(telegram_id: int, number: str, via_api: bool = False) -> int:
    rows = _run(
        """INSERT INTO calls (telegram_id, number, status, started_at, duration_sec, cost, via_api)
           VALUES (?, ?, 'ongoing', ?, 0, 0, ?) RETURNING id""",
        [telegram_id, number, now_iso(), 1 if via_api else 0],
    )
    return rows[0]["id"] if rows else None


def set_call_edesy_id(call_id: int, edesy_call_id: str):
    _run("UPDATE calls SET edesy_call_id = ? WHERE id = ?", [edesy_call_id, call_id])


def update_call_progress(call_id: int, duration_sec: int, cost: float):
    _run("UPDATE calls SET duration_sec = ?, cost = ? WHERE id = ?", [duration_sec, cost, call_id])


def end_call(call_id: int, status: str, duration_sec: int, cost: float):
    _run(
        "UPDATE calls SET status = ?, ended_at = ?, duration_sec = ?, cost = ? WHERE id = ?",
        [status, now_iso(), duration_sec, cost, call_id],
    )


def get_ongoing_calls():
    return _run("SELECT * FROM calls WHERE status = 'ongoing'")


def get_call(call_id: int):
    rows = _run("SELECT * FROM calls WHERE id = ?", [call_id])
    return rows[0] if rows else None
