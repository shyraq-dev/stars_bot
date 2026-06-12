import random
import string
from datetime import datetime


def generate_referral_code(tg_id: int) -> str:
    """Уникальды реферал коды жасау"""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"REF{tg_id}{suffix}"


def format_datetime(dt_str: str) -> str:
    """ISO datetime → оқылатын форматқа"""
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return dt_str


def status_emoji(status: str) -> str:
    return {
        "pending": "⏳",
        "paid": "✅",
        "cancelled": "❌",
        "rejected": "🚫",
    }.get(status, "❓")


def status_text(status: str) -> str:
    return {
        "pending": "Күтуде",
        "paid": "Расталды",
        "cancelled": "Жойылды",
        "rejected": "Қабылданбады",
    }.get(status, status)
