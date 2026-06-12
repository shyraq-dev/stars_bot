import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
    ADMIN_IDS: List[int] = field(default_factory=lambda: [
        int(x) for x in os.getenv("ADMIN_IDS", "123456789").split(",") if x.strip()
    ])

    # Database
    DB_PATH: str = os.getenv("DB_PATH", "stars_bot.db")

    # Channel & Support
    CHANNEL_URL: str     = os.getenv("CHANNEL_URL", "https://t.me/your_channel")
    SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "@username")


config = Config()
