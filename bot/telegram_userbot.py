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

Only replies in private 1:1 chats, and only to messages from the other
side — it never reacts to your own outgoing messages, so you can still
use this Telegram account normally alongside it.

--- Local run (interactive login, file-based session) ---
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

--- Deploying 24/7 (Render or any host without a terminal you can log in from) ---
A host like Render can't do the interactive phone/code prompt above, and
its filesystem doesn't persist a `.session` file across deploys anyway.
So instead:

1. Locally, run `python -m bot.generate_userbot_session` once (same
   TG_API_ID/TG_API_HASH) — it logs you in interactively, same as above,
   and prints a portable session string instead of saving a file.
2. Set that string as `TG_SESSION_STRING` in the host's environment
   variables (paste it directly in the host's dashboard, not in chat —
   treat it exactly like a password, because it is one).
3. Deploy this module normally (`python -m bot.telegram_userbot`) with
   `TG_SESSION_STRING` set — it skips the interactive login entirely and
   reconnects straight from the string, kept in memory only.
4. If the host is a Render *Web Service* (as opposed to a Background
   Worker), it expects something listening on `$PORT` or it'll consider
   the deploy unhealthy. This module starts a trivial `/health` responder
   on `$PORT` when that variable is set, purely to satisfy that check —
   it doesn't receive Telegram traffic, Pyrogram's own MTProto connection
   to Telegram's servers does all the real work.
"""
import asyncio
import http.server
import logging
import os
import threading

from pyrogram import Client, filters, idle
from pyrogram.enums import ChatAction
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
SESSION_STRING = os.environ.get("TG_SESSION_STRING")
SESSION_PATH = os.environ.get("TG_SESSION_PATH", "sveta_userbot")

if SESSION_STRING:
    # Deployed mode: no local file at all, session lives in the env var.
    app = Client("sveta_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)
else:
    # Local mode: file-based session, interactive login on first run.
    app = Client(SESSION_PATH, api_id=API_ID, api_hash=API_HASH)


def session_id_for(chat_id: int) -> str:
    return f"{PERSONA}-tguser-{chat_id}"


# Real people don't answer instantly. Pace the reply to roughly how long it
# would take a person to type it, and show the "typing..." indicator for
# that stretch instead of the reply just appearing.
TYPING_CHARS_PER_SECOND = 12
TYPING_MIN_DELAY = 1.0
TYPING_MAX_DELAY = 6.0


def _typing_delay(text: str) -> float:
    return min(TYPING_MAX_DELAY, max(TYPING_MIN_DELAY, len(text) / TYPING_CHARS_PER_SECOND))


async def _show_typing(client: Client, chat_id: int, seconds: float) -> None:
    # A single send_chat_action only keeps the indicator up for ~5s, so
    # refresh it in a loop for longer waits.
    elapsed = 0.0
    while elapsed < seconds:
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        step = min(4.0, seconds - elapsed)
        await asyncio.sleep(step)
        elapsed += step


@app.on_message(filters.private & filters.incoming & filters.text)
async def handle_message(client: Client, message: Message) -> None:
    sid = session_id_for(message.chat.id)
    import httpx

    try:
        async with httpx.AsyncClient(timeout=90.0) as http_client:
            resp = await http_client.post(
                f"{API_BASE}/api/chat", json={"session_id": sid, "message": message.text, "persona": PERSONA},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        log.warning("chat request failed: %s", e)
        await message.reply("что-то не так со связью, попробуй ещё раз чуть позже")
        return

    reply = data["reply"]
    await _show_typing(client, message.chat.id, _typing_delay(reply))
    await message.reply(reply)


@app.on_message(filters.private & filters.incoming & (filters.photo | filters.video | filters.video_note | filters.voice | filters.audio))
async def handle_real_media(_client: Client, message: Message) -> None:
    await message.reply("слушай, я не открываю фото и видео от малознакомых людей) давай пока просто словами")


class _HealthHandler(http.server.BaseHTTPRequestHandler):
    """Answers Render's (or any platform's) port-binding health check.

    Not part of the actual conversation — Pyrogram talks to Telegram over
    its own MTProto connection, this just proves *something* is listening
    on $PORT so a Web Service host doesn't consider the deploy dead.
    """

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def log_message(self, *args) -> None:
        pass  # don't spam the app log with health-check hits


def _start_health_server(port: int) -> None:
    server = http.server.HTTPServer(("0.0.0.0", port), _HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log.info("Health endpoint listening on :%s (for the host's port check only)", port)


async def _main() -> None:
    port = os.environ.get("PORT")
    if port:
        _start_health_server(int(port))

    async with app:
        log.info("Sveta AI Telegram userbot (%s) running, API_BASE=%s", PERSONA, API_BASE)
        await idle()


def run() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    run()
