from fastapi import APIRouter
from app.schemas.chat_schema import ChatRequest,ChatResponse
from app.services.chat_service import chat
import logging
logger = logging.getLogger(__name__)
from app.db.load_data import load_data

router = APIRouter()

@router.post("/chat",response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
  chatRes = await chat(request.text) 
  if(chatRes):
    # dispatch_action("")
    # db_data = load_data(collection_name="book")
    # logger.info(f"data loaded to db : {db_data}")
    # logger.info("route res --------", chatRes)
    return chatRes