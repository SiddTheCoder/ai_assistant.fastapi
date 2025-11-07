from fastapi import APIRouter
from app.schemas.chat_schema import ChatRequest,ChatResponse
from app.services.chat_service import chat
import logging
logger = logging.getLogger(__name__)
from app.db.load_data import load_data
import threading
from app.services.actions.action_dispatcher import dispatch_action

router = APIRouter()

@router.post("/chat",response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
  chatRes = await chat(request.text) 
  if(chatRes):
    threading.Thread(target=dispatch_action, args=("open_app",{"app_name": "notepad", 
   "content": "Hello there its me siddhant yadav . currently building an ai assistant"
   })).start()
    # dispatch_action("")
    # db_data = load_data(collection_name="book")
    # logger.info(f"data loaded to db : {db_data}")
    # logger.info("route res --------", chatRes)
    return chatRes