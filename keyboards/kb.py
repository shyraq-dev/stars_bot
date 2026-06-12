from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict


# ─── НЕГІЗГІ МӘЗІР (inline) ───────────────────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    """
    Хабарлама ішіндегі инлайн мәзір:
    [⭐ Жұлдыздар сатып алу]
    [👤 Бейін]  [📢 Біздің арна]
    [ℹ️ Қолдау көрсету]
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Жұлдыздар сатып алу", callback_data="buy_stars")
    builder.button(text="👤 Бейін",              callback_data="menu_profile")
    builder.button(text="📢 Біздің арна",         callback_data="menu_channel")
    builder.button(text="ℹ️ Қолдау көрсету",       callback_data="menu_support")
    builder.adjust(1, 2, 1)
    return builder.as_markup()


# ─── ЖҰЛДЫЗ САНЫ ЕНГІЗУ ──────────────────────────────────────────────────────

def stars_entry_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Артқа", callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()


# ─── КІМГЕ ЖІБЕРУ ─────────────────────────────────────────────────────────────

def recipient_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Өзіме",  callback_data="recipient_self")
    builder.button(text="🎁 Досыма", callback_data="recipient_other")
    builder.button(text="🔙 Артқа",  callback_data="buy_stars")
    builder.adjust(2, 1)
    return builder.as_markup()


# ─── ТӨЛЕМ ӘДІСІ ─────────────────────────────────────────────────────────────

def payment_method_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Kaspi (KZT)",  callback_data="pay_kzt")
    builder.button(text="💎 TON (Crypto)", callback_data="pay_ton")
    builder.button(text="🔙 Артқа",        callback_data="buy_stars")
    builder.adjust(1)
    return builder.as_markup()


# ─── KZT ТӨЛЕМ ───────────────────────────────────────────────────────────────

def kaspi_confirm_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Тапсырысты жою", callback_data=f"cancel_order:{order_id}")
    builder.adjust(1)
    return builder.as_markup()


def cancel_order_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Тапсырысты жою", callback_data=f"cancel_order:{order_id}")
    builder.adjust(1)
    return builder.as_markup()


# ─── ПРОФИЛЬ ──────────────────────────────────────────────────────────────────

def profile_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Сатып алу тарихы", callback_data="order_history")
    builder.button(text="🔗 Реферал сілтемесі", callback_data="my_referral")
    builder.button(text="🔙 Артқа",             callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()


def back_profile_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Бейінге оралу", callback_data="back_profile")
    builder.adjust(1)
    return builder.as_markup()


# ─── ADMIN ───────────────────────────────────────────────────────────────────

def admin_panel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика",         callback_data="admin_stats")
    builder.button(text="💱 Бағамдар",            callback_data="admin_rates")
    builder.button(text="🎁 Реферал бонусы",      callback_data="admin_ref_bonus")
    builder.button(text="💳 Kaspi реквизиттер",   callback_data="admin_kaspi")
    builder.button(text="📨 Жаппай хабарлама",    callback_data="admin_broadcast")
    builder.button(text="📋 KZT тапсырыстар",     callback_data="admin_pending_kzt")
    builder.button(text="👥 Қолданушыларды басқару",    callback_data="admin_ban")
    builder.adjust(2)
    return builder.as_markup()


def admin_order_kb(order_id: int, user_id: int, currency: str = "KZT") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Растау",     callback_data=f"admin_confirm:{order_id}:{user_id}")
    builder.button(text="❌ Қабылдамау", callback_data=f"admin_reject:{order_id}:{user_id}")
    if currency == "KZT":
        builder.button(
            text="🏦 Kaspi шотын тексеру",
            url="https://kaspi.kz"
        )
    else:
        builder.button(
            text="💎 TON шотын тексеру",
            url="https://t.me/wallet/start?startapp"
        )
    builder.adjust(2, 1)
    return builder.as_markup()


def back_admin_kb() -> InlineKeyboardMarkup:
    """Тек 'Артқа' — алдыңғы бетке қайту"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Артқа", callback_data="admin_back")
    builder.adjust(1)
    return builder.as_markup()


def back_to_panel_kb() -> InlineKeyboardMarkup:
    """Тек 'Мәзірге оралу' — Әкімші тақтасының басына"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Мәзірге оралу", callback_data="admin_back")
    builder.adjust(1)
    return builder.as_markup()


def with_back_to_panel_kb(inner_kb: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    """Кез келген мәзірге 'Мәзірге оралу' батырмасын қосу"""
    builder = InlineKeyboardBuilder()
    for row in inner_kb.inline_keyboard:
        for btn in row:
            if btn.callback_data:
                builder.button(text=btn.text, callback_data=btn.callback_data)
            elif btn.url:
                builder.button(text=btn.text, url=btn.url)
    builder.button(text="🏠 Мәзірге оралу", callback_data="admin_back")
    builder.adjust(1)
    return builder.as_markup()
