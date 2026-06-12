import aiosqlite
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def init(self):
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._create_tables()
        await self._seed_settings()
        logger.info("✅ Database инициализацияланды")

    async def close(self):
        if self._conn:
            await self._conn.close()

    # ══════════════════════════════════════════════════════════════
    #  КЕСТЕЛЕР
    # ══════════════════════════════════════════════════════════════

    async def _create_tables(self):
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY,
                tg_id           INTEGER UNIQUE NOT NULL,
                username        TEXT    DEFAULT '',
                full_name       TEXT    DEFAULT '',
                referral_code   TEXT    UNIQUE,
                referred_by     INTEGER,
                referral_count  INTEGER DEFAULT 0,
                total_spent_kzt REAL    DEFAULT 0,
                total_spent_ton REAL    DEFAULT 0,
                created_at      TEXT    DEFAULT (datetime('now')),
                is_banned       INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS orders (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                package_id      INTEGER DEFAULT 0,
                stars           INTEGER NOT NULL,
                amount_kzt      REAL    NOT NULL,
                amount_ton      REAL    DEFAULT 0,
                currency        TEXT    NOT NULL,
                payment_method  TEXT    NOT NULL,
                recipient       TEXT    DEFAULT '',
                status          TEXT    DEFAULT 'pending',
                crypto_invoice_id TEXT  DEFAULT '',
                created_at      TEXT    DEFAULT (datetime('now')),
                paid_at         TEXT,
                FOREIGN KEY(user_id) REFERENCES users(tg_id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS star_packages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                stars      INTEGER NOT NULL,
                label      TEXT    NOT NULL,
                is_active  INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_orders_user   ON orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
        """)
        await self._conn.commit()

    # ══════════════════════════════════════════════════════════════
    #  SEED
    # ══════════════════════════════════════════════════════════════

    async def _seed_settings(self):
        defaults = [
            ("star_price_kzt",     "13"),
            ("ton_price_kzt",      "800"),
            ("referral_bonus_kzt", "500"),
            ("kaspi_phone",        "+7 700 000 00 00"),
            ("kaspi_card",         "4400 4300 0000 0000"),
            ("kaspi_holder",       "АТЫ-ЖӨНІ"),
        ]
        for key, value in defaults:
            await self._conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
        await self._conn.commit()

    # ══════════════════════════════════════════════════════════════
    #  SETTINGS
    # ══════════════════════════════════════════════════════════════

    async def get_setting(self, key: str) -> Optional[str]:
        async with self._conn.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ) as cur:
            row = await cur.fetchone()
            return row["value"] if row else None

    async def set_setting(self, key: str, value: str):
        await self._conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)",
            (key, value)
        )
        await self._conn.commit()

    async def get_rates(self) -> Dict:
        star_kzt  = float(await self.get_setting("star_price_kzt")     or "13")
        ton_kzt   = float(await self.get_setting("ton_price_kzt")      or "800")
        ref_bonus = float(await self.get_setting("referral_bonus_kzt") or "500")
        return {
            "star_kzt":  star_kzt,
            "ton_kzt":   ton_kzt,
            "ref_bonus": ref_bonus,
        }

    # ══════════════════════════════════════════════════════════════
    #  USERS
    # ══════════════════════════════════════════════════════════════

    async def get_or_create_user(self, tg_id: int, username: str,
                                  full_name: str, referral_code: str,
                                  referred_by: Optional[int] = None) -> Dict:
        async with self._conn.execute(
            "SELECT * FROM users WHERE tg_id=?", (tg_id,)
        ) as cur:
            row = await cur.fetchone()

        if row:
            await self._conn.execute(
                "UPDATE users SET username=?, full_name=? WHERE tg_id=?",
                (username, full_name, tg_id)
            )
            await self._conn.commit()
            return dict(row)

        await self._conn.execute(
            """INSERT INTO users
               (tg_id, username, full_name, referral_code, referred_by)
               VALUES (?,?,?,?,?)""",
            (tg_id, username, full_name, referral_code, referred_by)
        )
        await self._conn.commit()

        async with self._conn.execute(
            "SELECT * FROM users WHERE tg_id=?", (tg_id,)
        ) as cur:
            return dict(await cur.fetchone())

    async def get_user(self, tg_id: int) -> Optional[Dict]:
        async with self._conn.execute(
            "SELECT * FROM users WHERE tg_id=?", (tg_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def get_user_by_referral(self, code: str) -> Optional[Dict]:
        async with self._conn.execute(
            "SELECT * FROM users WHERE referral_code=?", (code,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def update_spent(self, tg_id: int, amount_kzt: float,
                           currency: str, amount_ton: float = 0):
        if currency == "KZT":
            await self._conn.execute(
                "UPDATE users SET total_spent_kzt=total_spent_kzt+? WHERE tg_id=?",
                (amount_kzt, tg_id)
            )
        else:
            await self._conn.execute(
                "UPDATE users SET total_spent_ton=total_spent_ton+?, "
                "total_spent_kzt=total_spent_kzt+? WHERE tg_id=?",
                (amount_ton, amount_kzt, tg_id)
            )
        await self._conn.commit()

    async def increment_referral_count(self, tg_id: int):
        await self._conn.execute(
            "UPDATE users SET referral_count=referral_count+1 WHERE tg_id=?",
            (tg_id,)
        )
        await self._conn.commit()

    async def get_all_user_ids(self) -> List[int]:
        async with self._conn.execute(
            "SELECT tg_id FROM users WHERE is_banned=0"
        ) as cur:
            return [r["tg_id"] for r in await cur.fetchall()]

    async def get_user_count(self) -> int:
        async with self._conn.execute(
            "SELECT COUNT(*) as cnt FROM users"
        ) as cur:
            return (await cur.fetchone())["cnt"]

    async def ban_user(self, tg_id: int):
        await self._conn.execute(
            "UPDATE users SET is_banned=1 WHERE tg_id=?", (tg_id,)
        )
        await self._conn.commit()

    async def unban_user(self, tg_id: int):
        await self._conn.execute(
            "UPDATE users SET is_banned=0 WHERE tg_id=?", (tg_id,)
        )
        await self._conn.commit()

    async def get_banned_users(self) -> List[Dict]:
        async with self._conn.execute(
            "SELECT tg_id, username, full_name FROM users "
            "WHERE is_banned=1 ORDER BY full_name"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    # ══════════════════════════════════════════════════════════════
    #  ORDERS
    # ══════════════════════════════════════════════════════════════

    async def create_order(self, user_id: int, package_id: int,
                           stars: int, amount_kzt: float, currency: str,
                           payment_method: str, amount_ton: float = 0,
                           recipient: str = "") -> int:
        async with self._conn.execute(
            """INSERT INTO orders
               (user_id, package_id, stars, amount_kzt, amount_ton,
                currency, payment_method, recipient)
               VALUES (?,?,?,?,?,?,?,?)""",
            (user_id, package_id, stars, amount_kzt, amount_ton,
             currency, payment_method, recipient)
        ) as cur:
            await self._conn.commit()
            return cur.lastrowid

    async def get_order(self, order_id: int) -> Optional[Dict]:
        async with self._conn.execute(
            "SELECT * FROM orders WHERE id=?", (order_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def set_order_invoice(self, order_id: int, invoice_id: str):
        await self._conn.execute(
            "UPDATE orders SET crypto_invoice_id=? WHERE id=?",
            (invoice_id, order_id)
        )
        await self._conn.commit()

    async def confirm_order(self, order_id: int):
        await self._conn.execute(
            "UPDATE orders SET status='paid', paid_at=datetime('now') WHERE id=?",
            (order_id,)
        )
        await self._conn.commit()

    async def cancel_order(self, order_id: int):
        await self._conn.execute(
            "UPDATE orders SET status='cancelled' WHERE id=?", (order_id,)
        )
        await self._conn.commit()

    async def get_user_orders(self, user_id: int, limit: int = 10) -> List[Dict]:
        async with self._conn.execute(
            """SELECT * FROM orders WHERE user_id=?
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def get_pending_orders(self) -> List[Dict]:
        async with self._conn.execute(
            """SELECT o.*, u.username, u.full_name
               FROM orders o JOIN users u ON o.user_id=u.tg_id
               WHERE o.status='pending'
               ORDER BY o.created_at ASC"""
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def get_pending_kzt_orders(self) -> List[Dict]:
        async with self._conn.execute(
            """SELECT o.*, u.username, u.full_name
               FROM orders o JOIN users u ON o.user_id=u.tg_id
               WHERE o.status='pending' AND o.currency='KZT'
               ORDER BY o.created_at ASC"""
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    # ══════════════════════════════════════════════════════════════
    #  PACKAGES
    # ══════════════════════════════════════════════════════════════

    async def get_packages(self) -> List[Dict]:
        async with self._conn.execute(
            "SELECT * FROM star_packages WHERE is_active=1 ORDER BY sort_order"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def get_package(self, pkg_id: int) -> Optional[Dict]:
        async with self._conn.execute(
            "SELECT * FROM star_packages WHERE id=?", (pkg_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    # ══════════════════════════════════════════════════════════════
    #  STATISTICS
    # ══════════════════════════════════════════════════════════════

    async def get_stats(self) -> Dict:
        async with self._conn.execute(
            "SELECT COUNT(*) as cnt FROM users"
        ) as cur:
            users = (await cur.fetchone())["cnt"]

        async with self._conn.execute(
            "SELECT COUNT(*) as cnt, COALESCE(SUM(amount_kzt),0) as total "
            "FROM orders WHERE status='paid' AND currency='KZT'"
        ) as cur:
            kzt = await cur.fetchone()

        async with self._conn.execute(
            "SELECT COUNT(*) as cnt, COALESCE(SUM(amount_ton),0) as total_ton, "
            "COALESCE(SUM(amount_kzt),0) as total_kzt "
            "FROM orders WHERE status='paid' AND currency='TON'"
        ) as cur:
            ton = await cur.fetchone()

        async with self._conn.execute(
            "SELECT COALESCE(SUM(stars),0) as total FROM orders WHERE status='paid'"
        ) as cur:
            stars = (await cur.fetchone())["total"]

        return {
            "users":        users,
            "kzt_orders":   kzt["cnt"],
            "kzt_total":    kzt["total"],
            "ton_orders":   ton["cnt"],
            "ton_total":    ton["total_ton"],
            "ton_total_kzt":ton["total_kzt"],
            "stars_sold":   stars,
        }
