from fastapi import APIRouter
from app.schemas.chat_schema import ChatRequest,ChatResponse
from app.services.chat_service import chat
import logging
logger = logging.getLogger(__name__)
router = APIRouter()
from app.cache.load_user import log_cache_performance

@router.post("/chat",response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
  chatRes = await chat(request.text, request.user_id)
  a = log_cache_performance()
  logger.info(f"Cache Performance: {a}")
  if(chatRes):
    return chatRes