"""Telegram front-end for Sveta AI.

Just another client of the same public API the web chat uses — it never
imports backend/ directly, so it works exactly the same whether SVETA_API_BASE
points at http://127.0.0.1:8000 (local) or a deployed Render URL. Each
Telegram chat gets its own session_id, so the same backend can serve the
web chat and both bots for different people at once without collisions.

Two run modes, same handlers:

Local/dev — long-polling, no public URL needed:
    pip install -r requirements-telegram.txt
    set TELEGRAM_BOT_TOKEN=...        (from @BotFather)
    set SVETA_API_BASE=http://127.0.0.1:8000
    set PERSONA=sveta                 (or sergey)
    python -m bot.telegram_bot        (run as a module from the project root, not `python bot/telegram_bot.py`)

Render free Web Service — webhook, so it can sleep between messages like
any other free service instead of needing a paid always-on worker:
    env: TELEGRAM_BOT_TOKEN, SVETA_API_BASE, PUBLIC_URL (this service's own URL), PERSONA
    start command: uvicorn bot.telegram_bot:fastapi_app --host 0.0.0.0 --port $PORT

Voice messages are transcribed locally with faster-whisper (optional —
falls back to a "не поняла голосовое" reply if it isn't installed) and fed
into the same text pipeline. Real photos/video from the trainee are never
accepted or stored — same principle as real passwords: this system only
ever sends pre-approved persona media, never ingests real user media.

Set TTS_ENABLED=true to also send each reply as an audio file (Piper,
local/free — see tts.py). Sent via reply_audio rather than reply_voice:
Telegram's native "voice message" bubble requires OGG/Opus specifically,
and adding an encoder just for that bubble style wasn't worth it — a plain
audio attachment carries the same text-to-speech track.
"""
import asyncio
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path

import httpx
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from bot import tts

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sveta-telegram-bot")

# httpx logs the full request URL at INFO level, which for Telegram API
# calls includes the bot token (https://api.telegram.org/bot<TOKEN>/...) —
# keep it at WARNING so the token never lands in application logs.
logging.getLogger("httpx").setLevel(logging.WARNING)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API_BASE = os.environ.get("SVETA_API_BASE", "http://127.0.0.1:8000").rstrip("/")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
PERSONA = os.environ.get("PERSONA", "sveta")
TTS_ENABLED = os.environ.get("TTS_ENABLED", "false").lower() == "true"
WEBHOOK_PATH = f"/telegram/webhook/{BOT_TOKEN.split(':')[0]}"

http_client = httpx.AsyncClient(timeout=90.0)
telegram_app = Application.builder().token(BOT_TOKEN).build()

_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        # "tiny" is noticeably worse at Russian than "base" for a modest
        # extra ~35MB of weights — worth the tradeoff on a free instance.
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return _whisper_model


def session_id_for(chat_id: int) -> str:
    return f"{PERSONA}-telegram-{chat_id}"


# Real people don't answer instantly. Pace the reply to roughly how long it
# would take a person to type it, and show Telegram's "typing..." indicator
# for that stretch instead of the reply just appearing.
TYPING_CHARS_PER_SECOND = 12
TYPING_MIN_DELAY = 1.0
TYPING_MAX_DELAY = 6.0


def _typing_delay(text: str) -> float:
    return min(TYPING_MAX_DELAY, max(TYPING_MIN_DELAY, len(text) / TYPING_CHARS_PER_SECOND))


async def _show_typing(chat_id: int, seconds: float) -> None:
    # A single send_chat_action only keeps the indicator up for ~5s, so
    # refresh it in a loop for longer waits.
    elapsed = 0.0
    while elapsed < seconds:
        await telegram_app.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        step = min(4.0, seconds - elapsed)
        await asyncio.sleep(step)
        elapsed += step


async def _send_chat(update: Update, user_text: str) -> None:
    sid = session_id_for(update.effective_chat.id)
    try:
        resp = await http_client.post(
            f"{API_BASE}/api/chat", json={"session_id": sid, "message": user_text, "persona": PERSONA},
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("chat request failed: %s", e)
        await update.message.reply_text("что-то не так со связью, попробуй ещё раз чуть позже")
        return

    data = resp.json()
    reply = data["reply"]
    await _show_typing(update.effective_chat.id, _typing_delay(reply))
    await update.message.reply_text(reply)
    if TTS_ENABLED:
        await _send_voice_reply(update, reply)
    for media in data.get("media", []):
        await _send_media(update, media)


async def _send_voice_reply(update: Update, text: str) -> None:
    audio_bytes = await asyncio.to_thread(tts.synthesize, text, PERSONA)
    if audio_bytes is None:
        return
    await update.message.reply_audio(BytesIO(audio_bytes), filename="reply.wav")


async def _send_media(update: Update, media: dict) -> None:
    file_path = media.get("file_path")
    if not file_path:
        caption = "[изображение скрыто до подтверждения]" if media.get("blurred") else f"[{media['description']}]"
        await update.message.reply_text(caption)
        return

    url = f"{API_BASE}/media/{file_path}"
    caption = None if media.get("blurred") else media.get("description")
    if media.get("media_type") == "video":
        await update.message.reply_video(url, caption=caption)
    else:
        await update.message.reply_photo(url, caption=caption)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("привет)")


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


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_chat(update, update.message.text)


def _transcribe(model, path: str) -> str:
    segments, _ = model.transcribe(path, language="ru")
    return " ".join(s.text for s in segments).strip()


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    voice = update.message.voice or update.message.audio
    try:
        model = _get_whisper_model()
    except ImportError:
        await update.message.reply_text("пока не умею слушать голосовые, напиши текстом)")
        return

    tg_file = await context.bot.get_file(voice.file_id)
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = Path(tmpdir) / "voice.ogg"
        await tg_file.download_to_drive(str(local_path))
        text = await asyncio.to_thread(_transcribe, model, str(local_path))

    if not text:
        await update.message.reply_text("не расслышала, скажи ещё раз или напиши текстом")
        return

    await _send_chat(update, text)


async def handle_real_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "слушай, я не открываю фото и видео от малознакомых людей) давай пока просто словами"
    )


telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("report", report))
telegram_app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
telegram_app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.VIDEO_NOTE, handle_real_media))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))


def run_polling() -> None:
    log.info("Sveta AI Telegram bot (%s) polling, API_BASE=%s", PERSONA, API_BASE)
    telegram_app.run_polling()


fastapi_app = None
try:
    from fastapi import BackgroundTasks, FastAPI, Request

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
        return {"ok": True, "persona": PERSONA}

    @fastapi_app.post(WEBHOOK_PATH)
    async def webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
        # Ack Telegram immediately — transcription + the LLM call can run
        # past Telegram's own webhook timeout, and a slow ack makes it
        # redeliver the same update (voice messages getting transcribed
        # more than once). Process the update after responding instead.
        update = Update.de_json(await request.json(), telegram_app.bot)
        background_tasks.add_task(telegram_app.process_update, update)
        return {"ok": True}

except ImportError:
    pass  # fastapi not installed — local polling mode only


if __name__ == "__main__":
    run_polling()
