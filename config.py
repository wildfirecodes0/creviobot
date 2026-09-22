"""
All configuration is read from environment variables (.env locally, or
Render's Environment tab in production). Nothing is hard-coded.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str = None, required: bool = False) -> str:
    val = os.getenv(name, default)
    if required and not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


# --- Telegram ---
BOT_TOKEN = _get("BOT_TOKEN", required=True)
CHANNEL_USERNAME = _get("CHANNEL_USERNAME", "@CrevioUpdates")   # for join-check
RATING_CHANNEL_USERNAME = _get("RATING_CHANNEL_USERNAME", "@CrevioUpdates")
SUPPORT_USERNAME = _get("SUPPORT_USERNAME", "CrevioSupport")     # no @ needed here
WEBHOOK_BASE_URL = _get("WEBHOOK_BASE_URL", required=True)       # e.g. https://crevio.onrender.com
TELEGRAM_WEBHOOK_SECRET = _get("TELEGRAM_WEBHOOK_SECRET", required=True)  # random string, put it in the URL path

# --- Bot behaviour ---
BOT_CURRENCY = _get("BOT_CURRENCY", "INR")
PORT = int(_get("PORT", "10000"))

# --- Cloudflare D1 ---
CF_ACCOUNT_ID = _get("CF_ACCOUNT_ID", required=True)
CF_D1_DATABASE_ID = _get("CF_D1_DATABASE_ID", required=True)
CF_API_TOKEN = _get("CF_API_TOKEN", required=True)

# --- Razorpay ---
RAZORPAY_KEY_ID = _get("RAZORPAY_KEY_ID", required=True)
RAZORPAY_KEY_SECRET = _get("RAZORPAY_KEY_SECRET", required=True)
RAZORPAY_WEBHOOK_SECRET = _get("RAZORPAY_WEBHOOK_SECRET", required=True)

# --- TRX / Tron wallet ---
TRX_WALLET_ADDRESS = _get("TRX_WALLET_ADDRESS", required=True)
TRON_API_KEY = _get("TRON_API_KEY", "")   # optional, TronGrid API key

# --- Edesy (call provider) ---
EDESY_API_KEY = _get("EDESY_API_KEY", required=True)
EDESY_BASE_URL = _get("EDESY_BASE_URL", "https://masking.edesy.in/api/v1")

# --- Business rules (all adjustable without touching code) ---
DEPOSIT_TIMEOUT_MIN = int(_get("DEPOSIT_TIMEOUT_MIN", "11"))
MIN_DEPOSIT_INR = float(_get("MIN_DEPOSIT_INR", "10"))
MIN_DEPOSIT_TRX = float(_get("MIN_DEPOSIT_TRX", "1"))
TRX_TO_CURRENCY_RATE = float(_get("TRX_TO_CURRENCY_RATE", "30"))   # 1 TRX = 30 currency
INR_TO_CURRENCY_RATE = float(_get("INR_TO_CURRENCY_RATE", "1"))    # 1 INR = 1 currency

CALL_RATE_PER_MIN = float(_get("CALL_RATE_PER_MIN", "3"))          # charged to user
EDESY_COST_PER_MIN = float(_get("EDESY_COST_PER_MIN", "1.5"))      # actual provider cost
BILLING_TICK_SECONDS = int(_get("BILLING_TICK_SECONDS", "5"))
MIN_CALL_START_BALANCE_MIN = float(_get("MIN_CALL_START_BALANCE_MIN", "1"))  # min minutes worth

API_MIN_BALANCE = float(_get("API_MIN_BALANCE", "1000"))
REFERRAL_BONUS = float(_get("REFERRAL_BONUS", "0.3"))

HISTORY_PAGE_SIZE = int(_get("HISTORY_PAGE_SIZE", "10"))
