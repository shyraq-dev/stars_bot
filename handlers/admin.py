import asyncio
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.db import Database
from keyboards.kb import admin_panel_kb, admin_order_kb, back_admin_kb, back_to_panel_kb
from services.delivery import deliver_stars
from config import config

logger = logging.getLogger(__name__)
router = Router()


def is_admin(uid: int) -> bool:
    return uid in config.ADMIN_IDS


class AdminStates(StatesGroup):
    set_star_price    = State()
    set_ton_price     = State()
    set_ref_bonus     = State()
    set_kaspi_phone   = State()
    set_kaspi_card    = State()
    set_kaspi_holder  = State()
    broadcast_message = State()
    ban_user_id       = State()
    unban_user_id     = State()


# ══════════════════════════════════════════════════
#  /admin — бастапқы хабарлама
# ══════════════════════════════════════════════════

@router.message(Command("admin"))
async def admin_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("🔧 <b>Әкімші тақтасы</b>", reply_markup=admin_panel_kb())


# ─── АРТҚА (edit_text) ───────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.clear()
    await call.message.edit_text("🔧 <b>Әкімші тақтасы</b>", reply_markup=admin_panel_kb())
    await call.answer()


# ══════════════════════════════════════════════════
#  СТАТИСТИКА  (edit_text)
# ══════════════════════════════════════════════════

@router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    s     = await db.get_stats()
    rates = await db.get_rates()
    await call.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пайдаланушылар: <b>{s['users']}</b>\n\n"
        f"💳 KZT тапсырыстар: <b>{s['kzt_orders']}</b>\n"
        f"   Табыс: <b>{int(s['kzt_total'])} ₸</b>\n\n"
        f"💎 TON тапсырыстар: <b>{s['ton_orders']}</b>\n"
        f"   TON: <b>{s['ton_total']} TON</b>\n"
        f"   ≈ KZT: <b>{int(s['ton_total_kzt'])} ₸</b>\n\n"
        f"⭐ Жіберілген жұлдыздар: <b>{s['stars_sold']}</b>\n\n"
        f"💱 1 ⭐ = {rates['star_kzt']} ₸  |  1 TON = {rates['ton_kzt']} ₸",
        reply_markup=back_to_panel_kb()
    )
    await call.answer()


# ══════════════════════════════════════════════════
#  БАҒАМДАР (edit_text)
# ══════════════════════════════════════════════════

@router.callback_query(F.data == "admin_rates")
async def admin_rates(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    rates = await db.get_rates()
    builder = InlineKeyboardBuilder()
    builder.button(text=f"⭐ 1 жұлдыз = {rates['star_kzt']} ₸  ✏️", callback_data="admin_set_star")
    builder.button(text=f"💎 1 TON = {rates['ton_kzt']} ₸  ✏️",      callback_data="admin_set_ton")
    builder.button(text="🏠 Мәзірге оралу", callback_data="admin_back")
    builder.adjust(1)
    await call.message.edit_text(
        f"💱 <b>Бағамдар</b>\n\n"
        f"⭐ 1 жұлдыз = <b>{rates['star_kzt']} ₸</b>\n"
        f"💎 1 TON = <b>{rates['ton_kzt']} ₸</b>\n\n"
        f"Өзгерту үшін батырманы басыңыз:",
        reply_markup=builder.as_markup()
    )
    await call.answer()


@router.callback_query(F.data == "admin_set_star")
async def set_star_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.set_star_price)
    await call.message.edit_text(
        "⭐ <b>1 жұлдыздың жаңа бағасын жіберіңіз (₸):</b>\n\nМысалы: <code>13</code>",
        reply_markup=back_admin_kb()
    )
    await call.answer()


@router.message(AdminStates.set_star_price)
async def save_star_price(message: Message, db: Database, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        val = float(message.text.strip().replace(",", "."))
        assert val > 0
    except Exception:
        await message.answer("❌ Дұрыс сан жіберіңіз. Мысалы: <code>13</code>")
        return
    await db.set_setting("star_price_kzt", str(val))
    await state.clear()
    rates = await db.get_rates()
    builder = InlineKeyboardBuilder()
    builder.button(text=f"⭐ 1 жұлдыз = {rates['star_kzt']} ₸  ✏️", callback_data="admin_set_star")
    builder.button(text=f"💎 1 TON = {rates['ton_kzt']} ₸  ✏️",      callback_data="admin_set_ton")
    builder.button(text="🏠 Мәзірге оралу", callback_data="admin_back")
    builder.adjust(1)
    await message.answer(
        f"✅ 1 ⭐ бағамы жаңартылды: <b>{val} ₸</b>\n\n"
        f"💱 <b>Бағамдар</b>\n\n"
        f"⭐ 1 жұлдыз = <b>{rates['star_kzt']} ₸</b>\n"
        f"💎 1 TON = <b>{rates['ton_kzt']} ₸</b>",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "admin_set_ton")
async def set_ton_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.set_ton_price)
    await call.message.edit_text(
        "💎 <b>1 TON-ның жаңа бағасын жіберіңіз (₸):</b>\n\nМысалы: <code>850</code>",
        reply_markup=back_admin_kb()
    )
    await call.answer()


@router.message(AdminStates.set_ton_price)
async def save_ton_price(message: Message, db: Database, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        val = float(message.text.strip().replace(",", "."))
        assert val > 0
    except Exception:
        await message.answer("❌ Дұрыс сан жіберіңіз. Мысалы: <code>850</code>")
        return
    await db.set_setting("ton_price_kzt", str(val))
    await state.clear()
    rates = await db.get_rates()
    builder = InlineKeyboardBuilder()
    builder.button(text=f"⭐ 1 жұлдыз = {rates['star_kzt']} ₸  ✏️", callback_data="admin_set_star")
    builder.button(text=f"💎 1 TON = {rates['ton_kzt']} ₸  ✏️",      callback_data="admin_set_ton")
    builder.button(text="🏠 Мәзірге оралу", callback_data="admin_back")
    builder.adjust(1)
    await message.answer(
        f"✅ 1 TON бағамы жаңартылды: <b>{val} ₸</b>\n\n"
        f"💱 <b>Бағамдар</b>\n\n"
        f"⭐ 1 жұлдыз = <b>{rates['star_kzt']} ₸</b>\n"
        f"💎 1 TON = <b>{rates['ton_kzt']} ₸</b>",
        reply_markup=builder.as_markup()
    )


# ══════════════════════════════════════════════════
#  РЕФЕРАЛ БОНУС (edit_text)
# ══════════════════════════════════════════════════

@router.callback_query(F.data == "admin_ref_bonus")
async def admin_ref_bonus(call: CallbackQuery, db: Database, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    rates = await db.get_rates()
    await state.set_state(AdminStates.set_ref_bonus)
    await call.message.edit_text(
        f"🎁 <b>Реферал бонусы</b>\n\n"
        f"Ағымдағы: <b>{rates['ref_bonus']:.0f} ₸</b> / адам\n\n"
        f"Жаңа мәнді жіберіңіз (₸):\nМысалы: <code>500</code>",
        reply_markup=back_admin_kb()
    )
    await call.answer()


@router.message(AdminStates.set_ref_bonus)
async def save_ref_bonus(message: Message, db: Database, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        val = float(message.text.strip().replace(",", "."))
        assert val >= 0
    except Exception:
        await message.answer("❌ Дұрыс сан жіберіңіз.")
        return
    await db.set_setting("referral_bonus_kzt", str(val))
    await state.clear()
    await message.answer(
        f"✅ Реферал бонусы: <b>{val:.0f} ₸</b> / адам\n\n"
        f"🔧 <b>Әкімші тақтасы</b>",
        reply_markup=admin_panel_kb()
    )


# ══════════════════════════════════════════════════
#  KASPI РЕКВИЗИТТЕР (edit_text)
# ══════════════════════════════════════════════════

async def _kaspi_menu_text_kb(db: Database):
    phone  = await db.get_setting("kaspi_phone")
    card   = await db.get_setting("kaspi_card")
    holder = await db.get_setting("kaspi_holder")
    builder = InlineKeyboardBuilder()
    builder.button(text="📱 Телефон", callback_data="admin_kaspi_phone")
    builder.button(text="💳 Карта",   callback_data="admin_kaspi_card")
    builder.button(text="👤 Иесі",    callback_data="admin_kaspi_holder")
    builder.button(text="🏠 Мәзірге оралу", callback_data="admin_back")
    builder.adjust(2, 1, 1)
    text = (
        f"💳 <b>Реквизиттер</b>\n\n"
        f"📱 Телефон: <code>{phone}</code>\n"
        f"💳 Карта: <code>{card}</code>\n"
        f"👤 Иесі: {holder}"
    )
    return text, builder.as_markup()


@router.callback_query(F.data == "admin_kaspi")
async def admin_kaspi(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    text, kb = await _kaspi_menu_text_kb(db)
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "admin_kaspi_phone")
async def set_kaspi_phone(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.set_kaspi_phone)
    await call.message.edit_text(
        "📱 Жаңа телефон нөмірін жіберіңіз:\n<code>+7 777 000 00 00</code>",
        reply_markup=back_admin_kb()
    )
    await call.answer()


@router.message(AdminStates.set_kaspi_phone)
async def save_kaspi_phone(message: Message, db: Database, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await db.set_setting("kaspi_phone", message.text.strip())
    await state.clear()
    text, kb = await _kaspi_menu_text_kb(db)
    await message.answer(f"✅ Телефон жаңартылды.\n\n{text}", reply_markup=kb)


@router.callback_query(F.data == "admin_kaspi_card")
async def set_kaspi_card(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.set_kaspi_card)
    await call.message.edit_text(
        "💳 Жаңа карта нөмірін жіберіңіз:\n<code>4400 4300 1234 5678</code>",
        reply_markup=back_admin_kb()
    )
    await call.answer()


@router.message(AdminStates.set_kaspi_card)
async def save_kaspi_card(message: Message, db: Database, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await db.set_setting("kaspi_card", message.text.strip())
    await state.clear()
    text, kb = await _kaspi_menu_text_kb(db)
    await message.answer(f"✅ Карта жаңартылды.\n\n{text}", reply_markup=kb)


@router.callback_query(F.data == "admin_kaspi_holder")
async def set_kaspi_holder(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.set_kaspi_holder)
    await call.message.edit_text(
        "👤 Карта иесінің атын жіберіңіз:\n<code>AIBEK SEITKALI</code>",
        reply_markup=back_admin_kb()
    )
    await call.answer()


@router.message(AdminStates.set_kaspi_holder)
async def save_kaspi_holder(message: Message, db: Database, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await db.set_setting("kaspi_holder", message.text.strip())
    await state.clear()
    text, kb = await _kaspi_menu_text_kb(db)
    await message.answer(f"✅ Иесі жаңартылды.\n\n{text}", reply_markup=kb)


@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.broadcast_message)
    await call.message.edit_text(
        "📨 <b>Жаппай хабарлама</b>\n\n"
        "Барлық пайдаланушыларға жіберілетін хабарламаны жіберіңіз.\n"
        "HTML тегтері (<b>bold</b>, <i>italic</i>) жұмыс істейді.",
        reply_markup=back_admin_kb()
    )
    await call.answer()


@router.message(AdminStates.broadcast_message)
async def broadcast_send(message: Message, db: Database, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    uids  = await db.get_all_user_ids()
    total = len(uids)
    status_msg = await message.answer(f"📨 Жіберілуде... (0/{total})")
    sent = failed = 0
    for i, uid in enumerate(uids):
        try:
            await message.bot.send_message(uid, message.text)
            sent += 1
        except Exception:
            failed += 1
        if (i + 1) % 25 == 0:
            try:
                await status_msg.edit_text(f"📨 Жіберілуде... ({i+1}/{total})")
            except Exception:
                pass
            await asyncio.sleep(0.5)
    await status_msg.edit_text(
        f"✅ <b>Жіберіп болды!</b>\n\n"
        f"✉️ Жіберілді: <b>{sent}</b>  ❌ Сәтсіз: <b>{failed}</b>\n\n"
        f"🔧 <b>Әкімші тақтасы</b>",
        reply_markup=admin_panel_kb()
    )


# ══════════════════════════════════════════════════
#  ТАПСЫРЫСТАР (edit_text + бөлек хаттар тапсырысқа)
# ══════════════════════════════════════════════════

@router.callback_query(F.data == "admin_pending_kzt")
async def admin_pending_orders(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    orders = await db.get_pending_orders()
    if not orders:
        await call.message.edit_text(
            "✅ Күтудегі тапсырыстар жоқ.",
            reply_markup=back_admin_kb()
        )
        await call.answer()
        return

    await call.message.edit_text(
        f"📋 <b>Күтудегі тапсырыстар: {len(orders)}</b>\n\n"
        f"Тапсырыстар төменде жіберілді 👇",
        reply_markup=back_admin_kb()
    )
    for order in orders[:10]:
        icon = "💳" if order["currency"] == "KZT" else "💎"
        amount_str = (
            f"{int(order['amount_kzt'])} ₸"
            if order["currency"] == "KZT"
            else f"{order.get('amount_ton', 0)} TON"
        )
        await call.message.answer(
            f"{icon} <b>#{order['id']} — {order['currency']}</b>\n"
            f"👤 {order.get('full_name','—')} (@{order.get('username') or '—'})\n"
            f"🆔 <code>{order['user_id']}</code>\n"
            f"⭐ {order['stars']} жұлдыз  |  💰 {amount_str}\n"
            f"📥 Алушы: {order.get('recipient','—')}",
            reply_markup=admin_order_kb(order["id"], order["user_id"])
        )
    await call.answer()


@router.callback_query(F.data.startswith("admin_confirm:"))
async def admin_confirm(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    _, order_id, user_id = call.data.split(":")
    order = await db.get_order(int(order_id))
    if not order or order["status"] != "pending":
        await call.answer("Тапсырыс жарамсыз немесе өңделген!", show_alert=True)
        return
    await deliver_stars(call.bot, db, int(order_id))
    # Тапсырыс хатынан батырмаларды алып тастау
    try:
        caption = (call.message.caption or "") + "\n\n✅ <b>РАСТАЛДЫ</b>"
        if call.message.caption:
            await call.message.edit_caption(caption, reply_markup=None)
        else:
            await call.message.edit_text(
                call.message.text + "\n\n✅ <b>РАСТАЛДЫ</b>",
                reply_markup=None
            )
    except Exception:
        pass
    await call.answer("✅ Расталды!", show_alert=True)


@router.callback_query(F.data.startswith("admin_reject:"))
async def admin_reject(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    _, order_id, user_id = call.data.split(":")
    order = await db.get_order(int(order_id))
    if not order or order["status"] != "pending":
        await call.answer("Тапсырыс жарамсыз немесе өңделген!", show_alert=True)
        return
    await db.cancel_order(int(order_id))
    try:
        await call.bot.send_message(
            int(user_id),
            f"❌ Өкінішке орай, <b>#{order_id}</b> тапсырысыңыз қабылданбады.\n\n"
            f"🧑‍💻 Себебін білу немесе мәселені реттеу үшін қолдау қызметіне жазыңыз: "
            f"{config.SUPPORT_USERNAME}"
        )
    except Exception:
        pass
    try:
        caption = (call.message.caption or "") + "\n\n❌ <b>ҚАБЫЛДАНБАДЫ</b>"
        if call.message.caption:
            await call.message.edit_caption(caption, reply_markup=None)
        else:
            await call.message.edit_text(
                call.message.text + "\n\n❌ <b>ҚАБЫЛДАНБАДЫ</b>",
                reply_markup=None
            )
    except Exception:
        pass
    await call.answer("❌ Қабылданбады.", show_alert=True)


# ══════════════════════════════════════════════════
#  БАН / БАНДАН АЛУ (edit_text)
# ══════════════════════════════════════════════════

@router.callback_query(F.data == "admin_ban")
async def admin_ban_menu(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="🚫 Бұғаттау",          callback_data="admin_do_ban")
    builder.button(text="✅ Бұғатты алу",        callback_data="admin_do_unban")
    builder.button(text="📋 Бұғатталғандар тізімі", callback_data="admin_banned_list")
    builder.button(text="🏠 Мәзірге оралу",      callback_data="admin_back")
    builder.adjust(2, 1, 1)
    await call.message.edit_text(
        "👥 <b>Қолданушыларды басқару</b>\n\nТаңдаңыз:",
        reply_markup=builder.as_markup()
    )
    await call.answer()


@router.callback_query(F.data == "admin_do_ban")
async def admin_ban_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.ban_user_id)
    await call.message.edit_text(
        "🚫 <b>Бұғаттау</b>\n\nTelegram ID жіберіңіз:",
        reply_markup=back_admin_kb()
    )
    await call.answer()


@router.message(AdminStates.ban_user_id)
async def do_ban(message: Message, db: Database, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uid  = int(message.text.strip())
        user = await db.get_user(uid)
        if not user:
            await message.answer(
                "❌ Пайдаланушы табылмады.\n\n🔧 <b>Әкімші тақтасы</b>",
                reply_markup=admin_panel_kb()
            )
            await state.clear()
            return
        await db.ban_user(uid)
        name = user.get("full_name") or str(uid)
        try:
            await message.bot.send_message(uid, "🚫 Сіздің аккаунтыңыз бұғатталды.")
        except Exception:
            pass
        await state.clear()
        await message.answer(
            f"🚫 <b>{name}</b> ({uid}) бұғатталды.\n\n🔧 <b>Әкімші тақтасы</b>",
            reply_markup=admin_panel_kb()
        )
    except ValueError:
        await state.clear()
        await message.answer(
            "❌ Дұрыс Telegram ID жіберіңіз (тек сандар).\n\n🔧 <b>Әкімші тақтасы</b>",
            reply_markup=admin_panel_kb()
        )


@router.callback_query(F.data == "admin_do_unban")
async def admin_unban_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.unban_user_id)
    await call.message.edit_text(
        "✅ <b>Бұғатты алу</b>\n\nTelegram ID жіберіңіз:",
        reply_markup=back_admin_kb()
    )
    await call.answer()


@router.message(AdminStates.unban_user_id)
async def do_unban(message: Message, db: Database, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uid  = int(message.text.strip())
        user = await db.get_user(uid)
        if not user:
            await message.answer(
                "❌ Пайдаланушы табылмады.\n\n🔧 <b>Әкімші тақтасы</b>",
                reply_markup=admin_panel_kb()
            )
            await state.clear()
            return
        await db.unban_user(uid)
        name = user.get("full_name") or str(uid)
        try:
            await message.bot.send_message(uid, "✅ Аккаунтыңызға қол жеткізу қалпына келтірілді.")
        except Exception:
            pass
        await state.clear()
        await message.answer(
            f"✅ <b>{name}</b> ({uid}) бұғатты алынды.\n\n🔧 <b>Әкімші тақтасы</b>",
            reply_markup=admin_panel_kb()
        )
    except ValueError:
        await state.clear()
        await message.answer(
            "❌ Дұрыс Telegram ID жіберіңіз (тек сандар).\n\n🔧 <b>Әкімші тақтасы</b>",
            reply_markup=admin_panel_kb()
        )


@router.callback_query(F.data == "admin_banned_list")
async def admin_banned_list(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    users = await db.get_banned_users()
    if not users:
        await call.message.edit_text(
            "📋 <b>Бұғатталғандар тізімі</b>\n\nБұғатталған қолданушылар жоқ.",
            reply_markup=back_to_panel_kb()
        )
        await call.answer()
        return

    lines = ["📋 <b>Бұғатталғандар тізімі</b>\n"]
    for u in users:
        name = u.get("full_name") or "—"
        uname = f"@{u['username']}" if u.get("username") else "username жоқ"
        lines.append(f"🚫 {name} ({uname}) — <code>{u['tg_id']}</code>")

    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=back_admin_kb()
    )
    await call.answer()
