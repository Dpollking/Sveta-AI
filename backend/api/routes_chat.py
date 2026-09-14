from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.schemas import ChatRequest, ChatResponsePublic
from backend.services.sveta_engine import handle_message

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponsePublic)
async def chat(req: ChatRequest, db: Session = Depends(get_db)) -> ChatResponsePublic:
    return await handle_message(db, req.session_id, req.message, persona=req.persona)
