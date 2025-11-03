from pydantic import BaseModel
from typing import List, Optional

class Confirmation(BaseModel):
    isConfirmed: bool
    actionRegardingQuestion: str

class ActionDetails(BaseModel):
    type: str
    query: str
    title: str
    artist: str
    topic: str
    platforms: List[str]
    app_name: str
    target: str
    location: str
    confirmation: Confirmation
    additional_info: dict

class ChatRequest(BaseModel):
  text: str

class ChatResponse(BaseModel):
  answer: str
  action: str | None = None
  emotion: str | str = "neutral"
  actionDetails: ActionDetails | None