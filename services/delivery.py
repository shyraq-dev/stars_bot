import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from database.db import Database
from config import config

logger = logging.getLogger(__name__)


async def deliver_stars(bot: Bot, db: Database, order_id: int) -> bool:
    order = await db.get_order(order_id)
    if not order:
        logger.error(f"Тапсырыс табылмады: #{order_id}")
        return False
    if order["status"] == "paid":
        logger.warning(f"Тапсырыс #{order_id} бұрын расталған")
        return True

    # 1. DB-да растау
    await db.confirm_order(order_id)

    # 2. Жұмсалғанды жаңарту
    await db.update_spent(
        order["user_id"],
        order["amount_kzt"],
        order["currency"],
        order.get("amount_ton") or 0,
    )

    # 3. Реферал бонусы
    user = await db.get_user(order["user_id"])
    if user and user.get("referred_by"):
        rates = await db.get_rates()
        bonus_kzt = rates["ref_bonus"]
        await db.increment_referral_count(user["referred_by"])
        try:
            await bot.send_message(
                user["referred_by"],
                f"🎁 <b>Реферал бонусы!</b>\n\n"
                f"Сіздің досыңыз тапсырыс берді!\n"
                f"Бонус: <b>{bonus_kzt:.0f} ₸</b>\n\n"
                f"Толығырақ: {config.SUPPORT_USERNAME}"
            )
        except Exception:
            pass

    # 4. Пайдаланушыға жеткізу хабарламасы
    currency = order["currency"]
    if currency == "KZT":
        payment_info = f"💰 {order['amount_kzt']:.0f} ₸ (Kaspi)"
    else:
        payment_info = f"💰 {order.get('amount_ton', 0)} TON (~{order['amount_kzt']:.0f} ₸)"

    try:
        await bot.send_message(
            order["user_id"],
            f"✅ <b>Тапсырысыңыз расталды!</b>\n\n"
            f"⭐ <b>{order['stars']} Telegram Stars</b> бірден аударылды!\n\n"
            f"📦 Тапсырыс: <code>#{order_id}</code>\n"
            f"{payment_info}\n\n"
            f"Рақмет! 🙏"
        )
    except TelegramBadRequest as e:
        logger.error(f"Пайдаланушыға хабарлама қатесі {order['user_id']}: {e}")

    logger.info(f"✅ #{order_id} — {order['stars']}⭐ ({currency}) → user {order['user_id']}")
    return True
