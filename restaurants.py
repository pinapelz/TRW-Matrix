import sqlite3
import random
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "restaurants.db")

SEED_DATA = [
]


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS restaurants (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                name     TEXT NOT NULL UNIQUE COLLATE NOCASE,
                note     TEXT NOT NULL DEFAULT '',
                added_by TEXT NOT NULL DEFAULT 'unknown'
            )
        """)
        conn.commit()

        row = conn.execute("SELECT COUNT(*) AS cnt FROM restaurants").fetchone()
        if row["cnt"] == 0:
            conn.executemany(
                "INSERT OR IGNORE INTO restaurants (name, note, added_by) VALUES (?, ?, ?)",
                SEED_DATA,
            )
            conn.commit()


def _format_restaurant(row: sqlite3.Row) -> str:
    return f"{row['name']}\n- {row['note']}\nAdded by {row['added_by']}"


def add_restaurant(name: str, note: str, added_by: str) -> str:
    name = name.strip()
    note = note.strip()
    if not name:
        return "❌ Restaurant name cannot be empty."
    with _get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM restaurants WHERE name = ?", (name,)
        ).fetchone()
        if existing:
            return f"❌ **{name}** is already in the list."
        conn.execute(
            "INSERT INTO restaurants (name, note, added_by) VALUES (?, ?, ?)",
            (name, note, added_by),
        )
        conn.commit()
    return f"✅ Added **{name}** to the restaurant list!"


def remove_restaurant(name: str) -> str:
    name = name.strip()
    if not name:
        return "❌ Please provide a restaurant name to remove."
    with _get_conn() as conn:
        existing = conn.execute(
            "SELECT id, name FROM restaurants WHERE name = ?", (name,)
        ).fetchone()
        if not existing:
            return f"❌ No restaurant named **{name}** found. Names are case-insensitive."
        actual_name = existing["name"]
        conn.execute("DELETE FROM restaurants WHERE id = ?", (existing["id"],))
        conn.commit()
    return f"🗑️ Removed **{actual_name}** from the restaurant list."




def find_restaurant(keyword: str = "") -> str:
    keyword = keyword.strip().lower()
    with _get_conn() as conn:
        if keyword:
            rows = conn.execute(
                "SELECT name, note, added_by FROM restaurants WHERE LOWER(note) LIKE ?",
                (f"%{keyword}%",),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT name, note, added_by FROM restaurants"
            ).fetchall()

    if not rows:
        if keyword:
            return f"🔍 No restaurants found with **{keyword}** in their notes."
        return "No restaurants in the list yet. Use !addrestaurant to add one!"

    pick = random.choice(rows)
    label = f'🎲 Random pick (keyword: "{keyword}"):' if keyword else "🎲 Random pick:"
    return f"{label}\n\n{_format_restaurant(pick)}"



HELP_TEXT = (
    "🍽️ Restaurant bot commands:\n"
    "  !addrestaurant <name> | <note>  — add a new restaurant (names must be unique)\n"
    "  !removerestaurant <name>        — remove a restaurant by name\n"
    "  !findrestaurant [keyword]       — get a random restaurant (optionally filtered by keyword in note)"
)


async def handle_restaurant_command(bot_api, room_id: str, sender: str, body: str):
    """
    Returns True if the message was handled as a restaurant command, False otherwise.
    Call this from your on_message_event listener.
    """
    stripped = body.strip()
    lower = stripped.lower()

    # Passive trigger: any message containing "where to eat"
    if "where to eat" in lower and not lower.startswith("!"):
        reply = find_restaurant()
        await bot_api.send_text_message(room_id, reply)
        return True

    if not lower.startswith("!"):
        return False

    # !addrestaurant <name> | <note>
    if lower.startswith("!addrestaurant"):
        rest = stripped[len("!addrestaurant"):].strip()
        if not rest:
            await bot_api.send_text_message(
                room_id,
                "Usage: !addrestaurant <name> | <note>\nExample: !addrestaurant Sushi Place | great omakase | 📍 Downtown",
            )
            return True
        if "|" in rest:
            name, _, note = rest.partition("|")
        else:
            name = rest
            note = ""
        # Derive a friendly display name from the Matrix sender ID (@user:server -> user)
        added_by = sender.lstrip("@").split(":")[0]
        reply = add_restaurant(name, note, added_by)
        await bot_api.send_text_message(room_id, reply)
        return True

    # !removerestaurant <name>
    if lower.startswith("!removerestaurant"):
        name = stripped[len("!removerestaurant"):].strip()
        if not name:
            await bot_api.send_text_message(
                room_id,
                "Usage: !removerestaurant <name>\nExample: !removerestaurant MCDONALDS",
            )
            return True
        reply = remove_restaurant(name)
        await bot_api.send_text_message(room_id, reply)
        return True

    # !findrestaurant [keyword]
    if lower.startswith("!findrestaurant"):
        keyword = stripped[len("!findrestaurant"):].strip()
        reply = find_restaurant(keyword)
        await bot_api.send_text_message(room_id, reply)
        return True

    # !restaurants (help alias)
    if lower.startswith("!restaurants"):
        await bot_api.send_text_message(room_id, HELP_TEXT)
        return True

    return False
