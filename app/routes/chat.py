from fastapi import APIRouter
from app.schemas.chat_schema import ChatRequest,ChatResponse
from app.services.chat_service import chat
import logging
logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat",response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
  chatRes = await chat(request.text,"692ea878402dfb977a5b183f")
  if(chatRes):
    return chatRes