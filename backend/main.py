from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.api.routes_admin import router as admin_router
from backend.api.routes_chat import router as chat_router
from backend.api.routes_session import router as session_router
from backend.core.config import ASSETS_DIR
from backend.core.database import init_db
from backend.llm.factory import get_llm_adapter


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Sveta AI — Safe Romance Fraud Simulator", version="0.4.0", lifespan=lifespan)


@app.get("/api/health")
async def health() -> dict:
    llm = get_llm_adapter()
    return {
        "ok": True,
        "mode": "local-first",
        "llm_provider": type(llm).__name__,
        "llm_reachable": await llm.health(),
    }


app.include_router(chat_router)
app.include_router(session_router)
app.include_router(admin_router)

app.mount("/admin", StaticFiles(directory=str(ASSETS_DIR / "admin"), html=True), name="admin")
app.mount("/", StaticFiles(directory=str(ASSETS_DIR / "frontend"), html=True), name="frontend")
