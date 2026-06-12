from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.db import Database
from keyboards.kb import (
    main_menu_kb, stars_entry_kb, recipient_kb,
    kaspi_confirm_kb, cancel_order_kb, admin_order_kb
)
from config import config

router = Router()


class BuyStates(StatesGroup):
    enter_stars    = State()
    enter_username = State()
    waiting_pdf    = State()   # KZT: PDF күту
    waiting_ton    = State()   # TON: скриншот күту


# ══════════════════════════════════════════════════════
#  1. ЖҰЛДЫЗ САНЫН ЕНГІЗУ
# ══════════════════════════════════════════════════════

@router.callback_query(F.data == "buy_stars")
async def buy_stars_entry(call: CallbackQuery, db: Database, state: FSMContext):
    await state.clear()
    rates = await db.get_rates()
    await call.message.edit_text(
        f"⭐ <b>Telegram Stars сатып алу</b>\n\n"
        f"💱 1 ⭐ = <b>{rates['star_kzt']} ₸</b>\n"
        f"💱 1 TON = <b>{rates['ton_kzt']} ₸</b>\n\n"
        f"Қанша жұлдыз алғыңыз келеді?\n"
        f"<i>Ең аз: 50, ең көп: 100 000</i>\n\n"
        f"Санды жазыңыз 👇",
        reply_markup=stars_entry_kb()
    )
    await state.set_state(BuyStates.enter_stars)


@router.message(BuyStates.enter_stars)
async def receive_stars_count(message: Message, db: Database, state: FSMContext):
    text = message.text.strip().replace(" ", "").replace(",", "")
    if not text.isdigit():
        await message.answer("❌ Тек сан жіберіңіз. Мысалы: <code>100</code>")
        return

    stars = int(text)
    if stars < 50:
        await message.answer("❌ Ең аз мөлшер — <b>50 жұлдыз</b>.")
        return
    if stars > 100_000:
        await message.answer("❌ Ең көп мөлшер — <b>100 000 жұлдыз</b>.")
        return

    rates     = await db.get_rates()
    price_kzt = round(stars * rates["star_kzt"])
    price_ton = round(price_kzt / rates["ton_kzt"], 4)

    # Деректерді state-ке сақта
    await state.update_data(stars=stars, price_kzt=price_kzt, price_ton=price_ton)

    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Өзіме",  callback_data="recipient_self")
    builder.button(text="🎁 Досыма", callback_data="recipient_other")
    builder.button(text="🔙 Артқа",  callback_data="buy_stars_back")
    builder.adjust(2, 1)

    await message.answer(
        f"⭐ <b>Саны: {stars} жұлдыз</b>\n\n"
        f"💰 KZT: <b>{price_kzt} ₸</b>\n"
        f"💎 TON: <b>{price_ton} TON</b>\n\n"
        f"Кімге жіберілсін?",
        reply_markup=builder.as_markup()
    )


# ══════════════════════════════════════════════════════
#  2. АЛУШЫ ТАҢДАУ
# ══════════════════════════════════════════════════════

@router.callback_query(F.data == "recipient_self")
async def recipient_self(call: CallbackQuery, state: FSMContext, db: Database):
    username = f"@{call.from_user.username}" if call.from_user.username else None
    if not username:
        await call.answer(
            "Username-іңіз жоқ! Telegram-да username орнатыңыз.",
            show_alert=True
        )
        return
    await state.update_data(recipient=username, recipient_label="өзіңізге")
    await state.set_state(None)
    data = await state.get_data()
    await call.message.edit_text(
        _payment_choice_text(data),
        reply_markup=_payment_method_kb()
    )


@router.callback_query(F.data == "recipient_other")
async def recipient_other(call: CallbackQuery, state: FSMContext):
    from aiogram.utils.keyboard import InlineKeyboardBuilder as IKB
    back_kb = IKB()
    back_kb.button(text="🔙 Артқа", callback_data="buy_stars")
    back_kb.adjust(1)
    await call.message.edit_text(
        "🎁 <b>Достың @username-ін жіберіңіз</b>\n\n"
        "Мысалы: <code>@dosym</code>",
        reply_markup=back_kb.as_markup()
    )
    await state.set_state(BuyStates.enter_username)


@router.message(BuyStates.enter_username)
async def receive_username(message: Message, state: FSMContext, db: Database):
    username = message.text.strip()
    if not username.startswith("@"):
        username = f"@{username}"
    if len(username) < 2:
        await message.answer("❌ Дұрыс @username жіберіңіз.")
        return

    await state.update_data(recipient=username, recipient_label="сыйлық")
    await state.set_state(None)
    data = await state.get_data()

    await message.answer(
        _payment_choice_text(data),
        reply_markup=_payment_method_kb()
    )


def _payment_choice_text(data: dict) -> str:
    stars     = data.get("stars", 0)
    price_kzt = data.get("price_kzt", 0)
    price_ton = data.get("price_ton", 0)
    recipient = data.get("recipient", "—")
    label     = data.get("recipient_label", "")
    label_str = f" ({label})" if label else ""
    return (
        f"⭐ Саны: <b>{stars} жұлдыз</b>\n"
        f"💰 KZT: <b>{price_kzt} ₸</b> | TON: <b>{price_ton}</b>\n"
        f"👤 Алушы: <b>{recipient}</b>{label_str}\n\n"
        f"💳 Теңге — тексеру қолмен.\n"
        f"💎 TON — тексеру қолмен (@Wallet).\n\n"
        f"Төлем әдісін таңдаңыз 👇"
    )


def _payment_method_kb():
    """Inline батырмалар — callback_data-да stars/price жоқ,
       FSM state-те сақталған деректерді қолданады."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Kaspi (KZT)",  callback_data="pay_kzt")
    builder.button(text="💎 TON (@Wallet)", callback_data="pay_ton")
    builder.button(text="🔙 Артқа",         callback_data="buy_stars")
    builder.adjust(1)
    return builder.as_markup()


# ══════════════════════════════════════════════════════
#  3. KZT — ҚОЛМЕН
# ══════════════════════════════════════════════════════

@router.callback_query(F.data == "pay_kzt")
async def pay_kzt(call: CallbackQuery, db: Database, state: FSMContext):
    data      = await state.get_data()
    stars     = data.get("stars")
    price_kzt = data.get("price_kzt")
    recipient = data.get("recipient", f"@{call.from_user.username or call.from_user.id}")

    if not stars:
        await call.answer(
            "Сессия мерзімі өтіп кетті. Қайтадан бастаңыз.",
            show_alert=True
        )
        await call.message.edit_text(
            "⚠️ Сессия аяқталды. Қайтадан бастаңыз.",
            reply_markup=main_menu_kb()
        )
        return

    order_id = await db.create_order(
        user_id=call.from_user.id,
        package_id=0,
        stars=stars,
        amount_kzt=price_kzt,
        currency="KZT",
        payment_method="kaspi",
        recipient=recipient,
    )

    kaspi_phone  = await db.get_setting("kaspi_phone")
    kaspi_card   = await db.get_setting("kaspi_card")
    kaspi_holder = await db.get_setting("kaspi_holder")

    await _notify_admins(
        call.bot, order_id=order_id, stars=stars,
        amount=price_kzt, currency="KZT",
        user=call.from_user, recipient=recipient
    )

    await state.set_state(BuyStates.waiting_pdf)
    await state.update_data(order_id=order_id)

    # Kaspi батырмалары
    kaspi_kb = InlineKeyboardBuilder()
    kaspi_kb.button(
        text="📱 Телефонға аудару",
        url="https://kaspi.kz/transfers/categories/kaspi-client"
    )
    kaspi_kb.button(
        text="💳 Картаға аудару",
        url="https://kaspi.kz/transfers/categories/card-to-card"
    )
    kaspi_kb.button(text="❌ Тапсырысты жою", callback_data=f"cancel_order:{order_id}")
    kaspi_kb.adjust(1)

    await call.message.edit_text(
        f"💳 <b>Kaspi арқылы төлем</b>\n\n"
        f"⭐ Жұлдыз: <b>{stars}</b>\n"
        f"👤 Алушы: <b>{recipient}</b>\n"
        f"💰 Сома: <b>{price_kzt} ₸</b>\n"
        f"📦 Тапсырыс: <code>#{order_id}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📱 Телефон: <code>{kaspi_phone}</code>\n"
        f"💳 Карта: <code>{kaspi_card}</code>\n"
        f"👤 {kaspi_holder}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📄 Аударым жасағаннан кейін осы чатқа\n"
        f"<b>PDF түбіртекті</b> жіберіңіз 👇\n\n"
        f"<i>Kaspi → Тарих → Операция → Бөлісу → PDF</i>",
        reply_markup=kaspi_kb.as_markup()
    )


@router.message(BuyStates.waiting_pdf, F.document)
async def receive_pdf(message: Message, db: Database, state: FSMContext):
    doc = message.document
    if doc.mime_type != "application/pdf":
        await message.answer("❌ Тек <b>PDF</b> форматындағы түбіртек жіберіңіз!")
        return

    data     = await state.get_data()
    order_id = data.get("order_id")
    if not order_id:
        await message.answer("Қате! /start арқылы қайтадан бастаңыз.")
        return

    order = await db.get_order(order_id)
    if not order or order["status"] != "pending":
        await state.clear()
        await message.answer("⚠️ Бұл тапсырыс жарамды емес.")
        return

    await state.clear()

    user    = await db.get_user(message.from_user.id)
    caption = (
        f"📄 <b>KZT — PDF түбіртек</b>\n\n"
        f"👤 {user.get('full_name','—')} (@{user.get('username') or '—'})\n"
        f"🆔 <code>{message.from_user.id}</code>\n"
        f"⭐ <b>{order['stars']} жұлдыз</b>\n"
        f"👤 Алушы: <b>{order.get('recipient','—')}</b>\n"
        f"💰 <b>{order['amount_kzt']:.0f} ₸</b>\n"
        f"📦 Тапсырыс: <code>#{order_id}</code>\n\n"
        f"Kaspi-ден ақша түскенін тексеріп, шешіміңізді қабылдаңыз 👇"
    )
    for admin_id in config.ADMIN_IDS:
        try:
            await message.bot.send_document(
                admin_id, document=doc.file_id,
                caption=caption,
                reply_markup=admin_order_kb(order_id, message.from_user.id, "KZT")
            )
        except Exception:
            pass

    await message.answer(
        f"✅ <b>PDF түбіртегіңіз жіберілді!</b>\n\n"
        f"📦 Тапсырыс: <code>#{order_id}</code>\n\n"
        f"Әкімші Kaspi-ді тексеріп, растаса жұлдыздарыңыз\n"
        f"<b>лезде</b> беріледі 🙏",
        reply_markup=main_menu_kb()
    )


@router.message(BuyStates.waiting_pdf)
async def wrong_file_kzt(message: Message):
    await message.answer(
        "📄 Тек <b>PDF түбіртек</b> қабылданады.\n"
        "<i>Kaspi → Тарих → Операция → Бөлісу → PDF</i>"
    )


# ══════════════════════════════════════════════════════
#  4. TON — @WALLET АРҚЫЛЫ ҚОЛМЕН
# ══════════════════════════════════════════════════════

@router.callback_query(F.data == "pay_ton")
async def pay_ton(call: CallbackQuery, db: Database, state: FSMContext):
    data      = await state.get_data()
    stars     = data.get("stars")
    price_kzt = data.get("price_kzt")
    price_ton = data.get("price_ton")
    recipient = data.get("recipient", f"@{call.from_user.username or call.from_user.id}")

    if not stars:
        await call.answer(
            "Сессия мерзімі өтіп кетті. Қайтадан бастаңыз.",
            show_alert=True
        )
        await call.message.edit_text(
            "⚠️ Сессия аяқталды. Қайтадан бастаңыз.",
            reply_markup=main_menu_kb()
        )
        return

    order_id = await db.create_order(
        user_id=call.from_user.id,
        package_id=0,
        stars=stars,
        amount_kzt=price_kzt,
        amount_ton=price_ton,
        currency="TON",
        payment_method="wallet",
        recipient=recipient,
    )

    await _notify_admins(
        call.bot, order_id=order_id, stars=stars,
        amount=price_ton, currency="TON",
        user=call.from_user, recipient=recipient
    )

    await state.set_state(BuyStates.waiting_ton)
    await state.update_data(order_id=order_id)

    ton_kb = InlineKeyboardBuilder()
    ton_kb.button(
        text="💎 @Wallet арқылы төлеу",
        url="https://t.me/wallet/start?startapp"
    )
    ton_kb.button(text="❌ Тапсырысты жою", callback_data=f"cancel_order:{order_id}")
    ton_kb.adjust(1)

    await call.message.edit_text(
        f"💎 <b>TON арқылы төлем</b>\n\n"
        f"⭐ Жұлдыз: <b>{stars}</b>\n"
        f"👤 Алушы: <b>{recipient}</b>\n"
        f"💰 Сома: <b>{price_ton} TON</b> (~{price_kzt} ₸)\n"
        f"📦 Тапсырыс: <code>#{order_id}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💎 TON: {config.SUPPORT_USERNAME}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Аударым жасағаннан кейін осы чатқа\n"
        f"<b>скриншот немесе txid</b> жіберіңіз 👇",
        reply_markup=ton_kb.as_markup()
    )


@router.message(BuyStates.waiting_ton, F.photo | F.document | F.text)
async def receive_ton_proof(message: Message, db: Database, state: FSMContext):
    data     = await state.get_data()
    order_id = data.get("order_id")
    if not order_id:
        await message.answer("Қате! /start арқылы қайтадан бастаңыз.")
        return

    order = await db.get_order(order_id)
    if not order or order["status"] != "pending":
        await state.clear()
        await message.answer("⚠️ Бұл тапсырыс жарамды емес.")
        return

    await state.clear()

    user    = await db.get_user(message.from_user.id)
    caption = (
        f"💎 <b>TON — Төлем дәлелі</b>\n\n"
        f"👤 {user.get('full_name','—')} (@{user.get('username') or '—'})\n"
        f"🆔 <code>{message.from_user.id}</code>\n"
        f"⭐ <b>{order['stars']} жұлдыз</b>\n"
        f"👤 Алушы: <b>{order.get('recipient','—')}</b>\n"
        f"💰 <b>{order.get('amount_ton',0)} TON</b> (~{order['amount_kzt']:.0f} ₸)\n"
        f"📦 Тапсырыс: <code>#{order_id}</code>\n\n"
        f"@Wallet-тен TON аударымын тексеріп, шешіміңізді беріңіз 👇"
    )

    for admin_id in config.ADMIN_IDS:
        try:
            if message.photo:
                await message.bot.send_photo(
                    admin_id, message.photo[-1].file_id,
                    caption=caption,
                    reply_markup=admin_order_kb(order_id, message.from_user.id, "TON")
                )
            elif message.document:
                await message.bot.send_document(
                    admin_id, message.document.file_id,
                    caption=caption,
                    reply_markup=admin_order_kb(order_id, message.from_user.id, "TON")
                )
            else:
                await message.bot.send_message(
                    admin_id,
                    caption + f"\n\n💬 txid: <code>{message.text}</code>",
                    reply_markup=admin_order_kb(order_id, message.from_user.id, "TON")
                )
        except Exception:
            pass

    await message.answer(
        f"✅ <b>Төлем дәлелі жіберілді!</b>\n\n"
        f"📦 Тапсырыс: <code>#{order_id}</code>\n\n"
        f"Әкімші @Wallet-ті тексеріп, растаса жұлдыздарыңыз\n"
        f"<b>лезде</b> беріледі 🙏",
        reply_markup=main_menu_kb()
    )


# ─── CANCEL ──────────────────────────────────────────

@router.callback_query(F.data.startswith("cancel_order:"))
async def cancel_order(call: CallbackQuery, db: Database, state: FSMContext):
    await state.clear()
    parts    = call.data.split(":")
    order_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    if order_id:
        order = await db.get_order(order_id)
        if order and order["user_id"] == call.from_user.id:
            await db.cancel_order(order_id)
            # Adminге хабарлама
            for admin_id in config.ADMIN_IDS:
                try:
                    await call.bot.send_message(
                        admin_id,
                        f"🗑 <b>Тапсырыс жойылды</b>\n\n"
                        f"👤 {call.from_user.full_name} "
                        f"(@{call.from_user.username or '—'})\n"
                        f"📦 Тапсырыс: <code>#{order_id}</code>\n"
                        f"⭐ {order['stars']} жұлдыз | "
                        f"💰 {order['amount_kzt']:.0f} ₸\n\n"
                        f"Қолданушы тапсырысты өзі жойды."
                    )
                except Exception:
                    pass

    await call.message.edit_text(
        "🗑 <b>Тапсырыс жойылды.</b>\n\nНегізгі мәзір:",
        reply_markup=main_menu_kb()
    )


@router.callback_query(F.data == "buy_stars_back")
async def buy_stars_back(call: CallbackQuery, db: Database, state: FSMContext):
    await state.clear()
    rates = await db.get_rates()
    from handlers.start import WELCOME_TEXT
    await call.message.edit_text(
        WELCOME_TEXT.format(
            name=call.from_user.full_name or "Пайдаланушы",
            star_kzt=rates["star_kzt"],
            ton_kzt=rates["ton_kzt"],
        ),
        reply_markup=main_menu_kb()
    )


# ─── ADMIN NOTIFICATION ──────────────────────────────

async def _notify_admins(bot, order_id, stars, amount, currency, user, recipient=""):
    from aiogram.types import User as TgUser
    full_name  = user.full_name if isinstance(user, TgUser) else user.get("full_name", "—")
    username   = f"@{user.username}" if (isinstance(user, TgUser) and user.username) else "—"
    user_id    = user.id if isinstance(user, TgUser) else user.get("tg_id", "?")
    icon       = "💳" if currency == "KZT" else "💎"
    amount_str = f"{amount:.0f} ₸" if currency == "KZT" else f"{amount} TON"

    text = (
        f"🔔 <b>Жаңа {currency} тапсырысы!</b>\n\n"
        f"👤 {full_name} ({username})\n"
        f"🆔 <code>{user_id}</code>\n"
        f"⭐ <b>{stars} жұлдыз</b>\n"
        f"👤 Алушы: <b>{recipient}</b>\n"
        f"💰 {icon} <b>{amount_str}</b>\n"
        f"📦 Тапсырыс: <code>#{order_id}</code>\n\n"
        f"Пайдаланушы түбіртек жіберіп жатыр..."
    )
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass
