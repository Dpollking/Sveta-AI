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

    llm_provider: str = "ollama"
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:7b"
    llm_timeout: float = 30.0

    rag_enabled: bool = True
    rag_persist_dir: str = "./data/chroma"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"

    admin_token: str = "change-me"
    knowledge_dir: str = "./knowledge"
    media_dir: str = "./media"

    def resolved(self, path: str) -> Path:
        """For writable, persistent paths (database, chroma index)."""
        p = Path(path)
        return p if p.is_absolute() else BASE_DIR / p

    def resolved_asset(self, path: str) -> Path:
        """For read-only bundled assets (knowledge/, media/, frontend/, admin/)."""
        p = Path(path)
        return p if p.is_absolute() else ASSETS_DIR / p


settings = Settings()
