import db

CATEGORY = "game"


def init_db():
    db.init_db()
    db.seed(CATEGORY)


def _format(row) -> str:
    note_line = f"\n- {row['note']}" if row['note'].strip() else ""
    return f"{row['name']}{note_line}\nAdded by {row['added_by']}"


HELP_TEXT = (
    "🎮 Game bot commands:\n"
    "  !addgame <name> [| <note>]  — add a new game (names must be unique, note is optional)\n"
    "  !removegame <name>        — remove a game by name\n"
    "  !findgame [keyword]       — get a random game (optionally filtered by keyword in note)"
)


async def handle_game_command(bot_api, room_id: str, sender: str, body: str, self_name: str):
    stripped = body.strip()
    lower = stripped.lower()

    # Passive trigger: any message containing "what to play"
    if "what to play" in lower and not lower.startswith("!"):
        after = lower.split("what to play", 1)[1].strip()
        if after.isdigit():
            index = int(after)
            total = db.count_items(CATEGORY)
            pick = db.get_item_by_index(CATEGORY, index)
            if pick is None:
                reply = f"❌ Index {index} is out of range. Valid range: 1–{total}."
            else:
                reply = f"#{index} from the list of considerations:\n\n{_format(pick)}"
        else:
            pick = db.find_item(CATEGORY)
            reply = f"Fresh from the list of considerations:\n\n{_format(pick)}" if pick else "No games in the list yet. Use !addgame to add one!"
        await bot_api.send_text_message(room_id, reply)
        return True

    if not lower.startswith("!"):
        return False

    # !addgame <name> | <note>
    if lower.startswith("!addgame"):
        rest = stripped[len("!addgame"):].strip()
        if not rest:
            await bot_api.send_text_message(
                room_id,
                "Usage: !addgame <name> [| <note>]\nExample: !addgame Minecraft | sandbox survival game\nExample: !addgame Minecraft",
            )
            return True
        if "|" in rest:
            name, _, note = rest.partition("|")
        else:
            name = rest
            note = ""
        added_by = sender.lstrip("@").split(":")[0]
        error = db.add_item(CATEGORY, name, added_by, note=note)
        reply = error if error else f"✅ I will add **{name.strip()}** to the list of considerations"
        await bot_api.send_text_message(room_id, reply)
        return True

    # !removegame <name>
    if lower.startswith("!removegame"):
        name = stripped[len("!removegame"):].strip()
        if not name:
            await bot_api.send_text_message(
                room_id,
                "Usage: !removegame <name>\nExample: !removegame Minecraft",
            )
            return True
        result = db.remove_item(CATEGORY, name)
        if result is None:
            reply = f"❌ No game named **{name}** found. Names are case-insensitive."
        else:
            reply = f"🗑️ Removed **{result}** from the game list."
        await bot_api.send_text_message(room_id, reply)
        return True

    # !games (help alias)
    if lower.startswith("!games"):
        await bot_api.send_text_message(room_id, HELP_TEXT)
        return True

    return False
