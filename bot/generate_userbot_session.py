"""One-time helper: log in to a Telegram account interactively and print a
portable session string for bot/telegram_userbot.py's deployed mode.

Run this locally, in a terminal you're sitting at (it'll ask for the phone
number, the login code Telegram sends, and your 2FA password if you have
one set):

    set TG_API_ID=...
    set TG_API_HASH=...
    python -m bot.generate_userbot_session

It prints a long string at the end. Set that as TG_SESSION_STRING in your
hosting platform's environment variables directly through its dashboard —
not by pasting it into a chat or committing it anywhere — and treat it
exactly like a password: anyone who has it can act as this Telegram
account without needing the login code again. Nothing is written to disk
by this script (login happens in memory only), so there's no local
session file to clean up afterwards.
"""
import asyncio
import os

from pyrogram import Client

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]


async def main() -> None:
    async with Client("sveta_userbot_setup", api_id=API_ID, api_hash=API_HASH, in_memory=True) as client:
        session_string = await client.export_session_string()

    print("\nTG_SESSION_STRING (set this in your host's env vars, then close this terminal):\n")
    print(session_string)
    print()


if __name__ == "__main__":
    asyncio.run(main())
