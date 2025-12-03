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
    verification_token : Optional[str] = None
    verification_token_expires: Optional[datetime] = None
    refresh_token: Optional[str] = None  # ⚠️ NEVER expose this

    # API KEYS MANAGEMENT
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    is_gemini_api_quota_reached: bool = False
    is_openrouter_api_quota_reached: bool = False

    # --- UTM Parameters and advertiser tracking ---
    advertiser_partner : Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


    # --- Preferences & Interests ---
    accepts_promotional_emails: bool = False
    language: str = "en"
    ai_gender: str = "male"
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
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    # --- Preferences & Interests ---
    accepts_promotional_emails: bool = False
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


# Minimal response for list endpoints or when you need less data
class UserMinimalResponse(BaseModel):
    id: str = Field(..., alias="_id")
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    theme: str = "light"
    language: str = "en"

    class Config:
        populate_by_name = True