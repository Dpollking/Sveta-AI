"""Telegram front-end for Sveta AI.

Just another client of the same public API the web chat uses — it never
imports backend/ directly, so it works exactly the same whether SVETA_API_BASE
points at http://127.0.0.1:8000 (local) or a deployed Render URL. Each
Telegram chat gets its own session_id, so the same backend can serve the
web chat and the bot for different people at once without collisions.

Two run modes, same handlers:

Local/dev — long-polling, no public URL needed:
    pip install -r requirements-telegram.txt
    set TELEGRAM_BOT_TOKEN=...        (from @BotFather)
    set SVETA_API_BASE=http://127.0.0.1:8000
    python bot/telegram_bot.py

Render free Web Service — webhook, so it can sleep between messages like
any other free service instead of needing a paid always-on worker:
    env: TELEGRAM_BOT_TOKEN, SVETA_API_BASE, PUBLIC_URL (this service's own URL)
    start command: uvicorn bot.telegram_bot:fastapi_app --host 0.0.0.0 --port $PORT
"""
import logging
import os
from contextlib import asynccontextmanager

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sveta-telegram-bot")

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API_BASE = os.environ.get("SVETA_API_BASE", "http://127.0.0.1:8000").rstrip("/")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
WEBHOOK_PATH = f"/telegram/webhook/{BOT_TOKEN.split(':')[0]}"

http_client = httpx.AsyncClient(timeout=30.0)
telegram_app = Application.builder().token(BOT_TOKEN).build()


def session_id_for(chat_id: int) -> str:
    return f"telegram-{chat_id}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("привет) я Света. пиши что хочешь, познакомимся)")


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sid = session_id_for(update.effective_chat.id)
    try:
        resp = await http_client.get(f"{API_BASE}/api/session/{sid}/report")
        resp.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("report request failed: %s", e)
        await update.message.reply_text("не получилось получить отчёт, попробуй позже")
        return

    data = resp.json()
    findings = "\n".join(f"• {f}" for f in data.get("findings", []))
    text = (
        f"Образовательный отчёт (день {data.get('day')})\n"
        f"Уровень риска: {data.get('risk_level')}\n\n"
        f"{findings or 'Явных красных флагов не обнаружено.'}\n\n"
        f"{data.get('recommendation', '')}"
    )
    await update.message.reply_text(text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sid = session_id_for(update.effective_chat.id)
    user_text = update.message.text

    try:
        resp = await http_client.post(f"{API_BASE}/api/chat", json={"session_id": sid, "message": user_text})
        resp.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("chat request failed: %s", e)
        await update.message.reply_text("что-то не так со связью, попробуй ещё раз чуть позже")
        return

    data = resp.json()
    await update.message.reply_text(data["reply"])
    for media in data.get("media", []):
        caption = "[изображение скрыто до подтверждения]" if media.get("blurred") else f"[{media['description']}]"
        await update.message.reply_text(caption)


telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("report", report))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


def run_polling() -> None:
    log.info("Sveta AI Telegram bot polling, API_BASE=%s", API_BASE)
    telegram_app.run_polling()


fastapi_app = None
try:
    from fastapi import FastAPI, Request

    @asynccontextmanager
    async def _lifespan(_app: "FastAPI"):
        await telegram_app.initialize()
        if PUBLIC_URL:
            await telegram_app.bot.set_webhook(f"{PUBLIC_URL}{WEBHOOK_PATH}")
            log.info("Webhook set to %s%s", PUBLIC_URL, WEBHOOK_PATH)
        await telegram_app.start()
        yield
        await telegram_app.stop()
        await telegram_app.shutdown()

    fastapi_app = FastAPI(lifespan=_lifespan)

    @fastapi_app.get("/health")
    async def health() -> dict:
        return {"ok": True}

    @fastapi_app.post(WEBHOOK_PATH)
    async def webhook(request: Request) -> dict:
        update = Update.de_json(await request.json(), telegram_app.bot)
        await telegram_app.process_update(update)
        return {"ok": True}

except ImportError:
    pass  # fastapi not installed — local polling mode only


if __name__ == "__main__":
    run_polling()
