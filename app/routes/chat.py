from fastapi import APIRouter
from app.schemas.chat_schema import ChatRequest,ChatResponse
from app.services.chat_service import chat

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
  chatRes = await chat(request.text) 
  if(chatRes):
    return ChatResponse(answer=chatRes["answer"], action=chatRes["action"])