import json
import re
import logging
from typing import Any
from app.schemas.chat_schema import ActionDetails, ChatResponse, Confirmation

logger = logging.getLogger(__name__)


def merge_with_schema(data: dict) -> ActionDetails:
    """Merge raw dict into ActionDetails schema."""
    confirmation_data = data.get("confirmation", {})
    confirmation_obj = Confirmation(
        isConfirmed=confirmation_data.get("isConfirmed", False),
        actionRegardingQuestion=confirmation_data.get("actionRegardingQuestion", "")
    )

    action_details = ActionDetails(
        type=data.get("type", ""),
        query=data.get("query", ""),
        title=data.get("title", ""),
        artist=data.get("artist", ""),
        topic=data.get("topic", ""),
        platforms=data.get("platforms", []),
        app_name=data.get("app_name", ""),
        target=data.get("target", ""),
        location=data.get("location", ""),
        confirmation=confirmation_obj,
        additional_info=data.get("additional_info", {})
    )
    return action_details


def clean_ai_response(raw_data: str) -> ChatResponse:
    """
    Lightweight wrapper to parse AI response JSON.
    Only cleans/unwraps if the response is malformed.
    If response is clean, just formats newlines in the answer.
    """
    try:
        # Remove markdown fenced blocks if present
        raw_data = raw_data.strip()
        if raw_data.startswith("```"):
            raw_data = re.sub(r"^```[a-zA-Z]*\n?", "", raw_data).rstrip("`").strip()

        # Parse JSON
        data: Any = json.loads(raw_data)

        # Handle double-encoded JSON (if entire response is a string)
        if isinstance(data, str):
            data = json.loads(data)

        # Check if response is malformed (entire JSON nested in "answer" field)
        if "answer" in data and isinstance(data["answer"], str):
            try:
                # Try to parse the answer field as JSON
                potential_nested = json.loads(data["answer"])
                # If it has the expected structure, unwrap it
                if isinstance(potential_nested, dict) and "actionDetails" in potential_nested:
                    logger.warning("Detected nested JSON in 'answer' field, unwrapping...")
                    data = potential_nested
            except (json.JSONDecodeError, TypeError):
                # Not JSON - it's just a regular string answer, continue normally
                pass

        # Format answer text (only clean newlines, keep it readable)
        answer = data.get("answer", "").strip()
        # Replace literal \n with actual newlines
        if "\\n" in answer:
            answer = answer.replace("\\n", "\n")

        # Merge actionDetails with schema
        action_details = merge_with_schema(data.get("actionDetails", {}))

        cleaned = ChatResponse(
            answer=answer,
            action=data.get("action", "").strip(),
            emotion=data.get("emotion", "neutral").strip(),
            actionDetails=action_details
        )

        # Use model_dump() instead of deprecated json() method
        logger.info(f"Cleaned response: {cleaned.model_dump()}")
        return cleaned

    except (json.JSONDecodeError, AttributeError, TypeError) as e:
        logger.error(f"Failed to parse AI response: {e}")
        # Return fallback response with raw data as answer
        default_action = ActionDetails(
            type="",
            query="",
            title="",
            artist="",
            topic="",
            platforms=[],
            app_name="",
            target="",
            location="",
            confirmation=Confirmation(isConfirmed=False, actionRegardingQuestion=""),
            additional_info={}
        )
        return ChatResponse(
            answer=raw_data.strip(),
            action="",
            emotion="neutral",
            actionDetails=default_action
        )


ACTION_DETAILS_SCHEMA = {
    "type": "",             # core action category (e.g., "play_song", "search", "open_app", "navigate", "message", "control_device")
    "query": "",            # raw query string / parsed phrase
    "title": "",            # for content titles (song, video, note, etc.)
    "artist": "",           # for music
    "topic": "",            # for search/news/weather
    "platforms": [],        # prioritized array like ["youtube", "musicplayer", "spotify"]
    "app_name": "",         # if opening or interacting with an app
    "target": "",           # recipient (for messages, reminders, calls)
    "location": "",         # for map/weather-based actions
    "additional_info": {},  # flexible dict for extension
}