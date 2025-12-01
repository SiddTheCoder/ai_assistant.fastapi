from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Dict, Optional, Any

class UserModel(BaseModel):
    user_id: str
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    created_at: datetime = datetime.utcnow()
    last_login: Optional[datetime] = None

    # --- Preferences & Interests ---
    language: str = "en"  # preferred language
    theme: str = "light"  # dark/light mode
    notifications_enabled: bool = True
    categories_of_interest: List[str] = []  # e.g., ['tech', 'movies', 'sports']
    favorite_brands: List[str] = []

    # --- Likes / Dislikes / Habits ---
    liked_items: List[str] = []  # could be product IDs, topics, media
    disliked_items: List[str] = []
    activity_habits: Dict[str, Any] = {}  # e.g., {"reading": "daily", "gaming": "weekly"}
    behavioral_tags: List[str] = []  # e.g., 'early_riser', 'fitness_enthusiast'

    # --- Memories / Notes ---
    personal_memories: List[Dict[str, Any]] = []  # {"title": str, "content": str, "timestamp": datetime}
    reminders: List[Dict[str, Any]] = []  # {"title": str, "due_date": datetime, "completed": bool}
    
    # --- System / Usage Metrics ---
    last_active_at: Optional[datetime] = None
    session_count: int = 0
    preferences_history: List[Dict[str, Any]] = []  # track changes over time

    # --- Miscellaneous ---
    custom_attributes: Dict[str, Any] = {}  # for any extra dynamic field

# Example usage
# user = UserModel(
#     user_id="user_123",
#     username="Sidd",
#     categories_of_interest=["AI", "Programming", "Gaming"],
#     liked_items=["Python", "Next.js"],
#     behavioral_tags=["night_owl", "coffee_lover"]
# )