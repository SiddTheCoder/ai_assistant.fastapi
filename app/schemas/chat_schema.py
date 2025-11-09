from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class Confirmation(BaseModel):
    isConfirmed: bool = False
    actionRegardingQuestion: str = ""

class AnswerDetails(BaseModel):
    """Extended answer information."""
    content: str = ""
    sources: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)
    additional_info: Dict = Field(default_factory=dict)

class ActionDetails(BaseModel):
    type: str = ""
    query: str = ""
    title: str = ""
    artist: str = ""
    topic: str = ""
    platforms: List[str] = Field(default_factory=list)
    app_name: str = ""
    target: str = ""
    location: str = ""
    searchResults: List[Dict] = Field(default_factory=list)
    confirmation: Confirmation = Field(default_factory=Confirmation)
    additional_info: Dict = Field(default_factory=dict)

class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)

class ChatResponse(BaseModel):
    answer: str
    action: str = ""
    emotion: str = "neutral"
    answerDetails: Optional[AnswerDetails] = None
    actionDetails: Optional[ActionDetails] = None
