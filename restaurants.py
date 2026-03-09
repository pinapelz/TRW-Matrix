import os
import db

CATEGORY = "restaurant"
OLD_DB_PATH = os.path.join(os.path.dirname(__file__), "restaurants.db")


def init_db():
    db.init_db()
    db.migrate_from(OLD_DB_PATH, CATEGORY)
    db.seed(CATEGORY)


def _format(row) -> str:
    return f"{row['name']}\n- {row['note']}\nAdded by {row['added_by']}"


HELP_TEXT = (
    "🍽️ Restaurant bot commands:\n"
    "  !addrestaurant <name> | <note>  — add a new restaurant (names must be unique)\n"
    "  !removerestaurant <name>        — remove a restaurant by name\n"
    "  !findrestaurant [keyword]       — get a random restaurant (optionally filtered by keyword in note)"
)


async def handle_restaurant_command(bot_api, room_id: str, sender: str, body: str, self_name: str):
    """
    Returns True if the message was handled as a restaurant command, False otherwise.
    Call this from your on_message_event listener.
    """
    stripped = body.strip()
    lower = stripped.lower()

    if ("where to eat"  in lower or "what to eat" in lower) and not lower.startswith("!") and self_name in lower:
        pick = db.find_item(CATEGORY)
        reply = f"🎲 Random pick:\n\n{_format(pick)}" if pick else "No restaurants in the list yet. Use !addrestaurant to add one!"
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
        added_by = sender.lstrip("@").split(":")[0]
        error = db.add_item(CATEGORY, name, added_by, note=note)
        reply = error if error else f"✅ Added **{name.strip()}** to the restaurant list!"
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
        result = db.remove_item(CATEGORY, name)
        if result is None:
            reply = f"❌ No restaurant named **{name}** found. Names are case-insensitive."
        else:
            reply = f"🗑️ Removed **{result}** from the restaurant list."
        await bot_api.send_text_message(room_id, reply)
        return True

    # !findrestaurant [keyword]
    if lower.startswith("!findrestaurant"):
        keyword = stripped[len("!findrestaurant"):].strip()
        pick = db.find_item(CATEGORY, keyword)
        if pick is None:
            reply = f"🔍 No restaurants found with **{keyword}** in their notes." if keyword else "No restaurants in the list yet. Use !addrestaurant to add one!"
        else:
            label = f'🎲 Random pick (keyword: "{keyword}"):' if keyword else "🎲 Random pick:"
            reply = f"{label}\n\n{_format(pick)}"
        await bot_api.send_text_message(room_id, reply)
        return True

    # !restaurants (help alias)
    if lower.startswith("!restaurants"):
        await bot_api.send_text_message(room_id, HELP_TEXT)
        return True

    return False
