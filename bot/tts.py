"""Text-to-speech for bot replies — Piper (local, free, CPU).

Voices auto-download on first use into a local cache dir (persists for the
life of the container; re-downloads after a Render redeploy, ~60MB each).
Falls back silently (returns None) if piper-tts isn't installed, so voice
replies are a pure add-on, never a hard dependency.
"""
import logging
import wave
from io import BytesIO
from pathlib import Path

log = logging.getLogger("sveta-tts")

VOICE_BY_PERSONA = {
    "sveta": "ru_RU-irina-medium",
    "sergey": "ru_RU-dmitri-medium",
}

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "piper_voices"
_voices: dict[str, object] = {}


def _load_voice(persona: str):
    voice_name = VOICE_BY_PERSONA.get(persona, VOICE_BY_PERSONA["sveta"])
    if voice_name in _voices:
        return _voices[voice_name]

    from piper.voice import PiperVoice
    import piper.download_voices as dv

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    onnx_path = CACHE_DIR / f"{voice_name}.onnx"
    if not onnx_path.exists():
        log.info("downloading piper voice %s", voice_name)
        dv.download_voice(voice_name, CACHE_DIR)

    voice = PiperVoice.load(str(onnx_path), config_path=str(CACHE_DIR / f"{voice_name}.onnx.json"))
    _voices[voice_name] = voice
    return voice


def synthesize(text: str, persona: str) -> bytes | None:
    """Returns WAV bytes, or None if piper isn't available/installed."""
    try:
        voice = _load_voice(persona)
    except ImportError:
        return None

    buf = BytesIO()
    with wave.open(buf, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
    return buf.getvalue()
