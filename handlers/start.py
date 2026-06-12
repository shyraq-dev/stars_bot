from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db import Database
from keyboards.kb import main_menu_kb
from utils.helpers import generate_referral_code
from config import config

router = Router()

WELCOME_TEXT = (
    "⭐ <b>Telegram Stars дүкеніне қош келдіңіз!</b>\n\n"
    "Сәлем, <b>{name}</b>! 👋\n\n"
    "💱 <b>Ағымдағы бағам:</b>\n"
    "  • 1 ⭐ = <b>{star_kzt} ₸</b>\n"
    "  • 1 TON = <b>{ton_kzt} ₸</b>\n\n"
    "Төменде бөлімді таңдаңыз 👇"
)


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database, state: FSMContext):
    await state.clear()

    tg_id     = message.from_user.id
    username  = message.from_user.username or ""
    full_name = message.from_user.full_name or "Пайдаланушы"

    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        ref_user = await db.get_user_by_referral(args[1])
        if ref_user and ref_user["tg_id"] != tg_id:
            referred_by = ref_user["tg_id"]

    ref_code = generate_referral_code(tg_id)
    user = await db.get_or_create_user(tg_id, username, full_name, ref_code, referred_by)

    if referred_by and user.get("referred_by") is None:
        try:
            await message.bot.send_message(
                referred_by,
                "🎉 Сіздің реферал сілтемеңіз арқылы жаңа пайдаланушы тіркелді!"
            )
        except Exception:
            pass

    rates = await db.get_rates()
    await message.answer(
        WELCOME_TEXT.format(
            name=full_name,
            star_kzt=rates["star_kzt"],
            ton_kzt=rates["ton_kzt"],
        ),
        reply_markup=main_menu_kb()
    )


# ─── МӘЗІР CALLBACK-ТЕРІ ──────────────────────────────────────────────────────

@router.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery, db: Database, state: FSMContext):
    await state.clear()
    rates = await db.get_rates()
    user  = call.from_user
    await call.message.edit_text(
        WELCOME_TEXT.format(
            name=user.full_name or "Пайдаланушы",
            star_kzt=rates["star_kzt"],
            ton_kzt=rates["ton_kzt"],
        ),
        reply_markup=main_menu_kb()
    )


@router.callback_query(F.data == "menu_channel")
async def menu_channel(call: CallbackQuery):
    await call.answer()
    await call.message.answer(
        f"📢 <b>Біздің ресми арна</b>\n\n"
        f"Жаңалықтар, акциялар:\n"
        f"👉 {config.CHANNEL_URL}"
    )


@router.callback_query(F.data == "menu_support")
async def menu_support(call: CallbackQuery):
    await call.answer()
    await call.message.answer(
        f"ℹ️ <b>Қолдау көрсету</b>\n\n"
        f"Сұрақтарыңыз болса:\n"
        f"👤 {config.SUPPORT_USERNAME}\n\n"
        f"Жұмыс уақыты: <b>09:00 – 23:00</b>"
    )
