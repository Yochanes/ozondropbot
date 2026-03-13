from __future__ import annotations

import aiosqlite
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class ProductView:
    product_id: int
    ozon_id: str
    title: str
    url: str
    current_price: float
    previous_price: float | None


class Database:
    def __init__(self, path: str):
        self.path = path

    async def connect(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self.path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    async def init(self) -> None:
        async with await self.connect() as db:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_id INTEGER UNIQUE NOT NULL,
                    premium_until TEXT,
                    check_interval_minutes INTEGER NOT NULL DEFAULT 30,
                    drop_threshold_percent REAL NOT NULL DEFAULT 5,
                    timezone TEXT NOT NULL DEFAULT 'UTC',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ozon_id TEXT UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    current_price REAL,
                    last_check TEXT
                );

                CREATE TABLE IF NOT EXISTS user_products (
                    user_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, product_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    price REAL NOT NULL,
                    old_price REAL,
                    promo TEXT,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                );
                """
            )
            await db.commit()

    async def ensure_user(self, tg_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with await self.connect() as db:
            await db.execute(
                """
                INSERT INTO users (tg_id, created_at)
                VALUES (?, ?)
                ON CONFLICT(tg_id) DO NOTHING
                """,
                (tg_id, now),
            )
            await db.commit()

    async def get_user(self, tg_id: int) -> aiosqlite.Row | None:
        async with await self.connect() as db:
            cur = await db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
            return await cur.fetchone()

    async def get_user_products_count(self, tg_id: int) -> int:
        async with await self.connect() as db:
            cur = await db.execute(
                """
                SELECT COUNT(*) AS c FROM user_products up
                JOIN users u ON u.id = up.user_id
                WHERE u.tg_id = ?
                """,
                (tg_id,),
            )
            row = await cur.fetchone()
            return int(row["c"])

    async def add_product_for_user(self, tg_id: int, ozon_id: str, url: str, title: str) -> int:
        now = datetime.now(timezone.utc).isoformat()
        async with await self.connect() as db:
            await db.execute(
                "INSERT INTO products (ozon_id, url, title) VALUES (?, ?, ?) ON CONFLICT(ozon_id) DO NOTHING",
                (ozon_id, url, title),
            )
            cur = await db.execute("SELECT id FROM products WHERE ozon_id = ?", (ozon_id,))
            product_id = (await cur.fetchone())["id"]
            await db.execute(
                """
                INSERT INTO user_products (user_id, product_id, created_at)
                SELECT u.id, ?, ? FROM users u WHERE u.tg_id = ?
                ON CONFLICT(user_id, product_id) DO NOTHING
                """,
                (product_id, now, tg_id),
            )
            await db.commit()
            return int(product_id)

    async def list_user_products(self, tg_id: int) -> list[ProductView]:
        async with await self.connect() as db:
            cur = await db.execute(
                """
                SELECT p.id AS product_id, p.ozon_id, p.title, p.url, p.current_price,
                (
                    SELECT ph.price FROM price_history ph
                    WHERE ph.product_id = p.id
                    ORDER BY ph.timestamp DESC
                    LIMIT 1 OFFSET 1
                ) AS previous_price
                FROM products p
                JOIN user_products up ON up.product_id = p.id
                JOIN users u ON u.id = up.user_id
                WHERE u.tg_id = ?
                ORDER BY up.created_at DESC
                """,
                (tg_id,),
            )
            rows = await cur.fetchall()
        return [ProductView(**dict(row)) for row in rows]

    async def delete_user_product(self, tg_id: int, ozon_id: str) -> bool:
        async with await self.connect() as db:
            cur = await db.execute(
                """
                DELETE FROM user_products
                WHERE user_id = (SELECT id FROM users WHERE tg_id = ?)
                AND product_id = (SELECT id FROM products WHERE ozon_id = ?)
                """,
                (tg_id, ozon_id),
            )
            await db.commit()
            return cur.rowcount > 0

    async def append_price(self, product_id: int, price: float, old_price: float | None = None, promo: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with await self.connect() as db:
            await db.execute(
                "INSERT INTO price_history (product_id, timestamp, price, old_price, promo) VALUES (?, ?, ?, ?, ?)",
                (product_id, now, price, old_price, promo),
            )
            await db.execute(
                "UPDATE products SET current_price = ?, last_check = ? WHERE id = ?",
                (price, now, product_id),
            )
            await db.commit()

    async def get_price_history(self, product_id: int, limit: int = 2000) -> list[dict[str, Any]]:
        async with await self.connect() as db:
            cur = await db.execute(
                "SELECT timestamp, price, old_price, promo FROM price_history WHERE product_id = ? ORDER BY timestamp ASC LIMIT ?",
                (product_id, limit),
            )
            rows = await cur.fetchall()
            return [dict(row) for row in rows]

    async def get_global_drops(self, threshold_percent: float, limit: int) -> list[dict[str, Any]]:
        async with await self.connect() as db:
            cur = await db.execute(
                """
                WITH ordered AS (
                    SELECT ph.product_id, ph.timestamp, ph.price,
                           LAG(ph.price) OVER (PARTITION BY ph.product_id ORDER BY ph.timestamp) AS prev_price
                    FROM price_history ph
                )
                SELECT p.title, p.url, o.prev_price, o.price, o.timestamp,
                       ROUND((o.prev_price - o.price) / o.prev_price * 100, 2) AS drop_percent
                FROM ordered o
                JOIN products p ON p.id = o.product_id
                WHERE o.prev_price IS NOT NULL
                  AND o.prev_price > 0
                  AND ((o.prev_price - o.price) / o.prev_price * 100) >= ?
                ORDER BY o.timestamp DESC
                LIMIT ?
                """,
                (threshold_percent, limit),
            )
            rows = await cur.fetchall()
            return [dict(row) for row in rows]

    async def iter_tracking_rows(self) -> list[dict[str, Any]]:
        async with await self.connect() as db:
            cur = await db.execute(
                """
                SELECT u.tg_id, u.premium_until, u.drop_threshold_percent, p.id AS product_id, p.ozon_id, p.url, p.title, p.current_price
                FROM user_products up
                JOIN users u ON u.id = up.user_id
                JOIN products p ON p.id = up.product_id
                """
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def update_user_settings(self, tg_id: int, check_interval_minutes: int | None = None, drop_threshold_percent: float | None = None, tz: str | None = None) -> None:
        fields = []
        values: list[Any] = []
        if check_interval_minutes is not None:
            fields.append("check_interval_minutes = ?")
            values.append(check_interval_minutes)
        if drop_threshold_percent is not None:
            fields.append("drop_threshold_percent = ?")
            values.append(drop_threshold_percent)
        if tz is not None:
            fields.append("timezone = ?")
            values.append(tz)
        if not fields:
            return
        values.append(tg_id)
        async with await self.connect() as db:
            await db.execute(f"UPDATE users SET {', '.join(fields)} WHERE tg_id = ?", values)
            await db.commit()
