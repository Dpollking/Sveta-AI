"""Telegram *user-account* front-end for Sveta AI.

An official Bot API account always carries Telegram's "BOT" badge next
to the name — a dead giveaway that breaks immersion for a romance-fraud
simulator. This module runs Sveta's backend conversation (same
`/api/chat` calls, same per-chat session model the web chat uses) from a
regular, personal Telegram account instead, via MTProto (Pyrogram) rather
than the Bot API.

READ THIS BEFORE RUNNING: automating a normal (non-bot) Telegram account
this way is against Telegram's Terms of Service (accounts are meant to be
operated by a human, not a script) and can get the account limited or
banned. Only run this against an account you own and are using for your
own self-testing — never against someone else's account, and never for
mass/unsolicited messaging.

Setup:
    pip install -r requirements-userbot.txt
    Get api_id / api_hash for your account from https://my.telegram.org/apps
    set TG_API_ID=...
    set TG_API_HASH=...
    set SVETA_API_BASE=http://127.0.0.1:8000
    set PERSONA=sveta                 (or sergey)
    python -m bot.telegram_userbot

First run asks for your phone number and the login code Telegram sends
you (and your 2FA password, if you have one set) right there in the
terminal — this has to happen on a terminal you're sitting at, not
headless CI, since nobody else can read that code for you. After a
successful login, Pyrogram saves the session to `sveta_userbot.session`
next to this file, so later runs reconnect silently without asking again.
Treat that .session file like a password — anyone who has it can act as
your Telegram account without needing the login code again.

Only replies in private 1:1 chats, and only to messages from the other
side — it never reacts to your own outgoing messages, so you can still
use this Telegram account normally alongside it.
"""
import logging
import os

from pyrogram import Client, filters
from pyrogram.types import Message

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sveta-telegram-userbot")

# httpx logs the full request URL at INFO level; keep it quiet even though
# no secret token appears in these URLs, for consistent log hygiene.
logging.getLogger("httpx").setLevel(logging.WARNING)

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
API_BASE = os.environ.get("SVETA_API_BASE", "http://127.0.0.1:8000").rstrip("/")
PERSONA = os.environ.get("PERSONA", "sveta")
SESSION_PATH = os.environ.get("TG_SESSION_PATH", "sveta_userbot")

app = Client(SESSION_PATH, api_id=API_ID, api_hash=API_HASH)


def session_id_for(chat_id: int) -> str:
    return f"{PERSONA}-tguser-{chat_id}"


@app.on_message(filters.private & filters.incoming & filters.text)
async def handle_message(_client: Client, message: Message) -> None:
    sid = session_id_for(message.chat.id)
    import httpx

    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            resp = await http_client.post(
                f"{API_BASE}/api/chat", json={"session_id": sid, "message": message.text, "persona": PERSONA},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        log.warning("chat request failed: %s", e)
        await message.reply("что-то не так со связью, попробуй ещё раз чуть позже")
        return

    await message.reply(data["reply"])


@app.on_message(filters.private & filters.incoming & (filters.photo | filters.video | filters.video_note | filters.voice | filters.audio))
async def handle_real_media(_client: Client, message: Message) -> None:
    await message.reply("слушай, я не открываю фото и видео от малознакомых людей) давай пока просто словами")


def run() -> None:
    log.info("Sveta AI Telegram userbot (%s) starting, API_BASE=%s", PERSONA, API_BASE)
    app.run()


if __name__ == "__main__":
    run()
