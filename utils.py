import re
import config


def fmt(amount) -> str:
    try:
        return f"{float(amount):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def fmt_minutes(seconds_or_minutes, is_seconds=False) -> str:
    minutes = (seconds_or_minutes / 60) if is_seconds else seconds_or_minutes
    return f"{minutes:.1f}" if minutes % 1 else str(int(minutes))


def ref_link(bot_username: str, telegram_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref_{telegram_id}"


INDIA_NUMBER_RE = re.compile(r"^\+91[6-9]\d{9}$")


def is_valid_india_number(number: str) -> bool:
    return bool(INDIA_NUMBER_RE.match(number.strip()))


def max_call_minutes(balance: float, rate_per_min: float) -> float:
    if rate_per_min <= 0:
        return 0
    return round(balance / rate_per_min, 1)
