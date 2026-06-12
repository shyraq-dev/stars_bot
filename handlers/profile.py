from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database.db import Database
from keyboards.kb import profile_kb, back_profile_kb, main_menu_kb
from utils.helpers import format_datetime, status_emoji, status_text

router = Router()


@router.callback_query(F.data == "menu_profile")
async def profile_entry(call: CallbackQuery, db: Database):
    user  = await db.get_user(call.from_user.id)
    rates = await db.get_rates()
    await call.message.edit_text(_profile_text(user, rates), reply_markup=profile_kb())


@router.callback_query(F.data == "back_profile")
async def back_profile(call: CallbackQuery, db: Database):
    user  = await db.get_user(call.from_user.id)
    rates = await db.get_rates()
    await call.message.edit_text(_profile_text(user, rates), reply_markup=profile_kb())


def _profile_text(user: dict, rates: dict) -> str:
    reg_date    = format_datetime(user.get("created_at", ""))
    ref_count   = user.get("referral_count", 0)
    bonus_total = ref_count * rates["ref_bonus"]
    return (
        f"👤 <b>Сіздің бейініңіз</b>\n\n"
        f"🆔 ID: <code>{user['tg_id']}</code>\n"
        f"👤 Аты: <b>{user.get('full_name', '—')}</b>\n"
        f"📅 Тіркелген: {reg_date}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Жұмсалды:</b>\n"
        f"   KZT: <b>{int(user.get('total_spent_kzt', 0))} ₸</b>\n"
        f"   TON: <b>{user.get('total_spent_ton', 0)} TON</b>\n\n"
        f"🎁 <b>Реферал:</b>\n"
        f"   Қосылған достар: <b>{ref_count}</b>\n"
        f"   Жалпы бонус: <b>{bonus_total:.0f} ₸</b>"
    )


@router.callback_query(F.data == "order_history")
async def order_history(call: CallbackQuery, db: Database):
    orders = await db.get_user_orders(call.from_user.id, limit=10)
    if not orders:
        await call.message.edit_text(
            "📋 <b>Сатып алу тарихы</b>\n\nСатып алулар жоқ.",
            reply_markup=back_profile_kb()
        )
        return

    lines = ["📋 <b>Соңғы сатып алулар</b>\n"]
    for o in orders:
        emoji = status_emoji(o["status"])
        date  = format_datetime(o["created_at"])
        label = f"{o['stars']} ⭐"
        lines.append(
            f"{emoji} <b>{label}</b> — {o['amount_kzt']:.0f} ₸\n"
            f"   📅 {date} | {status_text(o['status'])}"
        )
    await call.message.edit_text("\n\n".join(lines), reply_markup=back_profile_kb())


@router.callback_query(F.data == "my_referral")
async def my_referral(call: CallbackQuery, db: Database):
    user  = await db.get_user(call.from_user.id)
    rates = await db.get_rates()
    code  = user.get("referral_code", "")
    bot_username = (await call.bot.get_me()).username
    ref_link  = f"https://t.me/{bot_username}?start={code}"
    ref_count = user.get("referral_count", 0)
    bonus     = ref_count * rates["ref_bonus"]

    await call.message.edit_text(
        f"🔗 <b>Реферал бағдарламасы</b>\n\n"
        f"Сіздің сілтемеңіз:\n"
        f"<code>{ref_link}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Қосылған достар: <b>{ref_count}</b>\n"
        f"🎁 Бонус / адам: <b>{rates['ref_bonus']:.0f} ₸</b>\n"
        f"💰 Жалпы бонус: <b>{bonus:.0f} ₸</b>\n\n"
        f"📤 Сілтемені достарыңызбен бөлісіңіз!",
        reply_markup=back_profile_kb()
    )
