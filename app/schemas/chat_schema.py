from pydantic import BaseModel

class ChatRequest(BaseModel):
  text: str

class ChatResponse(BaseModel):
  answer: str
  action: str | None = None