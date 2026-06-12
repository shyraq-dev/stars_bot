from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.filters import CommandStart

from database.db import Database


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, db: Database):
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data["db"] = self.db

        # Пайдаланушы ID-ін алу
        tg_user = None
        if isinstance(event, Message):
            tg_user = event.from_user
        elif isinstance(event, CallbackQuery):
            tg_user = event.from_user

        if tg_user:
            # /start командасын бұғатталғандар да жібере алады —
            # олар тек "бұғатталдыңыз" хабарламасын алады
            is_start = (
                isinstance(event, Message)
                and event.text
                and event.text.startswith("/start")
            )

            db_user = await self.db.get_user(tg_user.id)

            if db_user and db_user.get("is_banned"):
                if isinstance(event, Message):
                    await event.answer(
                        "🚫 Сіздің аккаунтыңыз бұғатталған.\n"
                        "Сұрақ болса байланысыңыз."
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "🚫 Аккаунтыңыз бұғатталған.",
                        show_alert=True
                    )
                return  # handler-ге өтпейді

        return await handler(event, data)
