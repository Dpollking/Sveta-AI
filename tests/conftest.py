import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_sveta.db")
os.environ.setdefault("RAG_ENABLED", "false")
os.environ.setdefault("ADMIN_TOKEN", "test-token")
