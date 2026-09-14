import sys
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def _writable_base_dir() -> Path:
    """Where persistent, writable data (sqlite db, chroma index) lives.

    A PyInstaller onefile .exe extracts bundled files into a fresh temp
    directory on every run, so anything the app needs to survive a restart
    must live next to the .exe itself, not next to `__file__`.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def _bundled_assets_dir() -> Path:
    """Where read-only bundled assets (knowledge/frontend/admin/media) live."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return _writable_base_dir()


BASE_DIR = _writable_base_dir()
ASSETS_DIR = _bundled_assets_dir()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./data/sveta.db"

    # ollama | llama_cpp | vllm | anthropic
    llm_provider: str = "ollama"
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:7b"
    llm_timeout: float = 30.0
    # Only used by the llama_cpp/vllm providers (both OpenAI-compatible) —
    # required for a real hosted API (OpenRouter, Groq, Together, ...), not
    # needed for a local llama.cpp/vLLM server, which ignores it.
    llm_api_key: str = ""

    rag_enabled: bool = True
    rag_persist_dir: str = "./data/chroma"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"

    admin_token: str = "change-me"
    knowledge_dir: str = "./knowledge"
    media_dir: str = "./media"

    # Comma-separated invite codes gating access to the training bots — only
    # people enrolled by whoever runs the training program should reach a
    # persona. Empty string = no gate (open access, e.g. local development).
    invite_codes: str = ""

    def valid_invite_codes(self) -> set[str]:
        return {c.strip() for c in self.invite_codes.split(",") if c.strip()}

    def resolved(self, path: str) -> Path:
        """For writable, persistent paths (database, chroma index)."""
        p = Path(path)
        return p if p.is_absolute() else BASE_DIR / p

    def resolved_asset(self, path: str) -> Path:
        """For read-only bundled assets (knowledge/, media/, frontend/, admin/)."""
        p = Path(path)
        return p if p.is_absolute() else ASSETS_DIR / p


settings = Settings()
