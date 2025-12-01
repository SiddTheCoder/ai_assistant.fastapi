from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import List, Dict, Optional, Any

# Base model with ALL fields (for internal use/database)
class UserModel(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    is_user_verified: bool = False
    refresh_token: Optional[str] = None  # ⚠️ NEVER expose this

    # --- Preferences & Interests ---
    language: str = "en"
    theme: str = "light"
    notifications_enabled: bool = True
    categories_of_interest: List[str] = []
    favorite_brands: List[str] = []

    # --- Likes / Dislikes / Habits ---
    liked_items: List[str] = []
    disliked_items: List[str] = []
    activity_habits: Dict[str, Any] = {}
    behavioral_tags: List[str] = []

    # --- Memories / Notes ---
    personal_memories: List[Dict[str, Any]] = []
    reminders: List[Dict[str, Any]] = []
    
    # --- System / Usage Metrics ---
    last_active_at: Optional[datetime] = None
    session_count: int = 0
    preferences_history: List[Dict[str, Any]] = []

    # --- Miscellaneous ---
    custom_attributes: Dict[str, Any] = {}

    class Config:
        populate_by_name = True


# Response model for API endpoints (excludes sensitive data)
class UserResponse(BaseModel):
    id: str = Field(..., alias="_id")
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    # ✅ NO refresh_token here

    # --- Preferences & Interests ---
    language: str = "en"
    theme: str = "light"
    notifications_enabled: bool = True
    categories_of_interest: List[str] = []
    favorite_brands: List[str] = []

    # --- Likes / Dislikes / Habits ---
    liked_items: List[str] = []
    disliked_items: List[str] = []
    activity_habits: Dict[str, Any] = {}
    behavioral_tags: List[str] = []

    # --- Memories / Notes ---
    personal_memories: List[Dict[str, Any]] = []
    reminders: List[Dict[str, Any]] = []
    
    # --- System / Usage Metrics ---
    last_active_at: Optional[datetime] = None
    session_count: int = 0

    # --- Miscellaneous ---
    custom_attributes: Dict[str, Any] = {}

    class Config:
        populate_by_name = True


# Minimal response for list endpoints or when you need less data
class UserMinimalResponse(BaseModel):
    id: str = Field(..., alias="_id")
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    theme: str = "light"
    language: str = "en"

    class Config:
        populate_by_name = True