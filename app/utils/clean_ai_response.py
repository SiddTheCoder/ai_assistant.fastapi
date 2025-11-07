import json
import re
import logging
from typing import Any
from json_repair import repair_json
from app.schemas.chat_schema import (
    ActionDetails, 
    ChatResponse, 
    Confirmation, 
    AnswerDetails
)

logger = logging.getLogger(__name__)


def clean_ai_response(raw_data: str) -> ChatResponse:
    """
    Parse and validate AI response JSON with robust error handling.
    Handles markdown wrappers, nested JSON, and malformed responses.
    """
    try:
        # Step 1: Remove markdown code blocks
        raw_data = raw_data.strip()
        if raw_data.startswith("```"):
            raw_data = re.sub(r"^```[a-zA-Z]*\n?", "", raw_data)
            raw_data = raw_data.rstrip("`").strip()

        # Step 1.5: Repair malformed JSON
        try:
            raw_data = repair_json(raw_data)
        except Exception as e:
            logger.warning(f"JSON repair failed, proceeding with original: {e}")

        # Step 2: Parse JSON
        data: Any = json.loads(raw_data)

        # Step 3: Handle double-encoded JSON (string instead of dict)
        if isinstance(data, str):
            logger.warning("Response is double-encoded string, parsing again...")
            data = json.loads(data)

        # Step 4: Check for nested JSON in 'answer' field (common AI mistake)
        if "answer" in data and isinstance(data["answer"], str):
            try:
                # Try to repair nested JSON before parsing
                answer_str = data["answer"]
                try:
                    answer_str = repair_json(answer_str)
                except Exception:
                    pass
                
                potential_nested = json.loads(answer_str)
                if isinstance(potential_nested, dict) and "actionDetails" in potential_nested:
                    logger.warning("Unwrapping nested JSON from 'answer' field")
                    data = potential_nested
            except json.JSONDecodeError as je:
                logger.warning(f"Nested JSON in 'answer' is malformed: {je}")
                pass  # It's just a normal string answer
            except TypeError:
                pass

        # Step 5: Extract and validate fields
        answer = data.get("answer", "").strip()
        if "\\n" in answer:
            answer = answer.replace("\\n", "\n")

        action = data.get("action", "").strip()
        emotion = data.get("emotion", "neutral").strip()

        # Step 6: Parse answerDetails with defaults
        answer_details_data = data.get("answerDetails", {})
        answer_details = AnswerDetails(
            content=answer_details_data.get("content", ""),
            sources=answer_details_data.get("sources", []),
            references=answer_details_data.get("references", []),
            additional_info=answer_details_data.get("additional_info", {})
        )

        # Step 7: Parse actionDetails with schema validation
        action_details_data = data.get("actionDetails", {})
        action_details = _parse_action_details(action_details_data)

        # Step 8: Create validated response
        cleaned = ChatResponse(
            answer=answer,
            action=action,
            emotion=emotion,
            answerDetails=answer_details,
            actionDetails=action_details
        )

        logger.info(f"Successfully cleaned response: answer_length={len(answer)}, action={action}, emotion={emotion}")
        return cleaned

    except (json.JSONDecodeError, AttributeError, TypeError, KeyError) as e:
        logger.error(f"Failed to parse AI response: {e}", exc_info=True)
        logger.debug(f"Raw data causing error: {raw_data[:500]}...")
        
        # Return fallback with raw data as answer
        return _create_fallback_response(raw_data)


def _parse_action_details(data: dict) -> ActionDetails:
    """Parse and validate actionDetails with nested confirmation."""
    confirmation_data = data.get("confirmation", {})
    confirmation = Confirmation(
        isConfirmed=confirmation_data.get("isConfirmed", False),
        actionRegardingQuestion=confirmation_data.get("actionRegardingQuestion", "")
    )

    return ActionDetails(
        type=data.get("type", ""),
        query=data.get("query", ""),
        title=data.get("title", ""),
        artist=data.get("artist", ""),
        topic=data.get("topic", ""),
        platforms=data.get("platforms", []),
        app_name=data.get("app_name", ""),
        target=data.get("target", ""),
        location=data.get("location", ""),
        confirmation=confirmation,
        additional_info=data.get("additional_info", {})
    )


def _create_fallback_response(raw_data: str) -> ChatResponse:
    """Create safe fallback response when parsing fails."""
    return ChatResponse(
        answer=raw_data.strip() if raw_data else "Sorry, I couldn't process that response.",
        action="",
        emotion="neutral",
        answerDetails=AnswerDetails(
            content="",
            sources=[],
            references=[],
            additional_info={}
        ),
        actionDetails=ActionDetails(
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
    )