"""
Uses Razorpay's Payment Links API (simplest option — gives us a plain URL
to send in Telegram, no frontend/checkout.js needed).
"""
import hmac
import hashlib
import logging
from datetime import datetime, timedelta, timezone

import razorpay

import config

log = logging.getLogger("crevio.razorpay")

client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))


def create_payment_link(telegram_id: int, deposit_id: int, amount_inr: float) -> dict:
    """Creates a fixed-amount payment link that expires with our deposit window."""
    expire_by = int((datetime.now(timezone.utc) + timedelta(minutes=config.DEPOSIT_TIMEOUT_MIN)).timestamp())
    payload = {
        "amount": int(round(amount_inr * 100)),  # paise
        "currency": "INR",
        "description": "Crevio Bot Deposit",
        "reference_id": f"dep_{deposit_id}",
        "expire_by": expire_by,
        "notes": {
            "telegram_id": str(telegram_id),
            "deposit_id": str(deposit_id),
        },
        "notify": {"sms": False, "email": False},
    }
    link = client.payment_link.create(payload)
    return link  # contains 'short_url' and 'id'


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    expected = hmac.new(
        config.RAZORPAY_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")
