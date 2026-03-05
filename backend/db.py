"""Local SQLite persistence for saved users and progress."""
import aiosqlite
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "minesweeper.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS saved_users (
                name TEXT PRIMARY KEY,
                score INTEGER NOT NULL DEFAULT 0,
                games INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                best_time INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
        """)
        await db.commit()


async def get_saved_users() -> list[dict]:
    """Return list of saved users for scoreboard / load picker."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT name, score, games, wins, best_time FROM saved_users ORDER BY score DESC"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_user(name: str) -> dict | None:
    """Get one saved user by name, or None."""
    name = (name or "").strip()[:20] or None
    if not name:
        return None
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT name, score, games, wins, best_time FROM saved_users WHERE name = ?",
            (name,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def save_user(name: str, score: int, games: int, wins: int, best_time: int):
    """Upsert user progress."""
    name = (name or "").strip()[:20] or "Player"
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO saved_users (name, score, games, wins, best_time, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                score = excluded.score,
                games = excluded.games,
                wins = excluded.wins,
                best_time = excluded.best_time,
                updated_at = excluded.updated_at
            """,
            (name, max(0, score), max(0, games), max(0, wins), max(0, best_time), now),
        )
        await db.commit()
