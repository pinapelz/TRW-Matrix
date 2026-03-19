import sqlite3
import random
import os
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")
SEEDS_DIR = os.path.join(os.path.dirname(__file__), "seeds")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                category   TEXT NOT NULL COLLATE NOCASE,
                name       TEXT NOT NULL COLLATE NOCASE,
                note       TEXT NOT NULL DEFAULT '',
                added_by   TEXT NOT NULL DEFAULT 'unknown',
                UNIQUE(category, name)
            )
        """)
        conn.commit()


def load_seed_file(category: str) -> list[tuple[str, str, str]]:
    path = os.path.join(SEEDS_DIR, f"{category}.txt")
    if not os.path.exists(path):
        return []

    entries: list[tuple[str, str, str]] = []
    with open(path, encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f.readlines()]

    # Split on blank lines to get per-entry blocks
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)

    for block in blocks:
        if len(block) < 2:
            continue
        name = block[0].strip()
        if len(block) == 2:
            note = ""
            added_by = block[1].strip()
        else:
            note = block[1].strip()
            added_by = block[2].strip()
        if name:
            entries.append((name, note, added_by))

    return entries


def seed(category: str, entries: Optional[list[tuple[str, str, str]]] = None):
    if entries is None:
        entries = load_seed_file(category)
    if not entries:
        return
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM items WHERE category = ?", (category,)
        ).fetchone()
        if row["cnt"] == 0:
            conn.executemany(
                "INSERT OR IGNORE INTO items (category, name, note, added_by) VALUES (?, ?, ?, ?)",
                [(category, name, note, added_by) for name, note, added_by in entries],
            )
            conn.commit()


def add_item(category: str, name: str, added_by: str, note: str = "") -> str | None:
    name = name.strip()
    note = note.strip()
    category = category.strip()
    if not name:
        return "❌ Name cannot be empty."
    with _get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM items WHERE category = ? AND name = ?", (category, name)
        ).fetchone()
        if existing:
            return f"❌ **{name}** is already in the list."
        conn.execute(
            "INSERT INTO items (category, name, note, added_by) VALUES (?, ?, ?, ?)",
            (category, name, note, added_by),
        )
        conn.commit()
    return None


def remove_item(category: str, name: str) -> str | None:
    name = name.strip()
    if not name:
        return "❌ Please provide a name to remove."
    with _get_conn() as conn:
        existing = conn.execute(
            "SELECT id, name FROM items WHERE category = ? AND name = ?", (category, name)
        ).fetchone()
        if not existing:
            return None
        actual_name = existing["name"]
        conn.execute("DELETE FROM items WHERE id = ?", (existing["id"],))
        conn.commit()
    return actual_name


def count_items(category: str) -> int:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM items WHERE category = ?", (category,)
        ).fetchone()
    return row["cnt"]


def get_item_by_index(category: str, index: int) -> sqlite3.Row | None:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT name, note, added_by FROM items WHERE category = ? ORDER BY id ASC",
            (category,),
        ).fetchall()
    if not rows or index < 1 or index > len(rows):
        return None
    return rows[index - 1]


def find_item(category: str, keyword: str = "") -> sqlite3.Row | None:
    """Return a random item from the category, optionally filtered by keyword in note."""
    keyword = keyword.strip().lower()
    with _get_conn() as conn:
        if keyword:
            rows = conn.execute(
                "SELECT name, note, added_by FROM items WHERE category = ? AND LOWER(note) LIKE ?",
                (category, f"%{keyword}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT name, note, added_by FROM items WHERE category = ?", (category,)
            ).fetchall()
    if not rows:
        return None
    return random.choice(rows)


def migrate_from(old_db_path: str, category: str):
    if not os.path.exists(old_db_path):
        return

    old_conn = sqlite3.connect(old_db_path)
    old_conn.row_factory = sqlite3.Row
    try:
        tables = old_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        if not tables:
            return
        table_name = tables[0]["name"]
        rows = old_conn.execute(
            f"SELECT name, note, added_by FROM {table_name}"  # noqa: S608
        ).fetchall()
    finally:
        old_conn.close()

    if rows:
        with _get_conn() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO items (category, name, note, added_by) VALUES (?, ?, ?, ?)",
                [(category, r["name"], r["note"], r["added_by"]) for r in rows],
            )
            conn.commit()

    os.remove(old_db_path)
