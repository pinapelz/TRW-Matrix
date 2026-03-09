import simplematrixbotlib as botlib
import os
from dotenv import load_dotenv
import constants
import restaurants
import games

load_dotenv()

HOMESERVER = os.environ.get("HOMESERVER", "")
USERNAME = os.environ.get("USERNAME", "")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "")
TARGET_ROOM_ID = os.environ.get("TARGET_ROOM_ID", "")
SELF = os.environ.get("SELF")

creds = botlib.Creds(homeserver=HOMESERVER, username=USERNAME, access_token=ACCESS_TOKEN)
bot = botlib.Bot(creds)

restaurants.init_db()
games.init_db()


@bot.listener.on_message_event
async def trigger_responses(room, message):
    if message.sender == f"@{USERNAME}":
        return
    if room.room_id != TARGET_ROOM_ID:
        return

    if await restaurants.handle_restaurant_command(bot.api, room.room_id, message.sender, message.body, SELF):
        return

    if await games.handle_game_command(bot.api, room.room_id, message.sender, message.body, SELF):
        return

    msg_text = message.body.strip().lower()
    cleaned = ''.join(ch if ch.isalnum() else ' ' for ch in msg_text)
    words = cleaned.split()
    normalized = ' ' + ' '.join(words) + ' '
    match = None
    for key in constants.TRIGGERS:
        key_str = str(key).lower()
        key_clean = ''.join(ch if ch.isalnum() else ' ' for ch in key_str)
        key_norm = ' ' + ' '.join(key_clean.split()) + ' '
        if key_norm and key_norm in normalized:
            match = key
            break
    if match:
        msg_text = match
        await bot.api.send_text_message(room.room_id, f"{constants.TRIGGERS[msg_text]}")
bot.run()
