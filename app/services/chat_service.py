from app.utils import clean_ai_response, load_user_from_redis
from app.ai.providers.manager import ProviderManager
from typing import Optional
from app.config import settings
# from app.services.detect_emotion import detect_emotion
from app.db.pinecone.config import (get_user_all_queries,search_user_queries)
from app.cache.redis.config import get_last_n_messages,process_query_and_get_context
from app.prompts import app_prompt_en,app_prompt_hi,app_prompt_ne
import json
import logging

logger = logging.getLogger(__name__)

async def chat(
    query: str,
    user_id: str = "user_1",
    model_name: Optional[str] = None
):
    """
    Main chat function with smart AI provider fallback.
    
    Flow:
    1. Load user details (API keys, quota status)
    2. Get conversation context
    3. Build prompt
    4. Call AI with automatic Gemini → OpenRouter fallback
    5. Return cleaned response
    
    Args:
        query: User's message
        user_id: User identifier
        model_name: Optional model name for OpenRouter fallback
    
    Returns:
        ChatResponse with AI answer
    """
    if not query or not query.strip():
        return _create_error_response("Empty query received", "neutral")
    
    try:
        # --- Step 1: Load User Details ---
        user_details = await load_user_from_redis.load_user(user_id)

        if not user_details:
            logger.error(f"❌ Could not load user details for {user_id}")
            return _create_error_response(
                "User not found. Please log in again.",
                "neutral",
                query
            )
        print("BYPASS 1 -  USER from redis",user_details)

        # --- Step 2: Get Conversation Context ---
        query_context, is_pinecone_needed = process_query_and_get_context(user_id, query, search_user_queries, get_user_all_queries, threshold=0.2)

        logger.info(f"Query context from chat_service: {json.dumps(query_context, indent=2)}")

        # Get Local Context from redis
        recent_context = get_last_n_messages(user_id, n=10)
        logger.info(f"Recent context from chat_service: {json.dumps(recent_context, indent=2)}")

        # --- Step 3: Emotion Detection (placeholder) ---
        emotion = "neutral"
            
        # --- Step 4: Build Prompt ---
        prompt = app_prompt_hi.build_prompt_hi(emotion, query, recent_context, query_context)
        logger.info(f"📝 Prompt built: {prompt[:200]}...")

        # --- Step 5: Call AI with Smart Fallback ---
        provider_manager = ProviderManager(user_details)

        print("BYPASS 5 -  provide  manager",provider_manager)
        
        raw_response, provider_used = provider_manager.call_with_fallback(
            prompt=prompt,
            model_name=model_name or settings.openrouter_reasoning_model_name
        )

        print("BYPASS 5 -  raw response",raw_response)
        print("BYPASS 5 -  provider used",provider_used)
        
        logger.info(f"✅ Response received from {provider_used.value}")
        
        if not raw_response:
            return _create_error_response("Empty AI response", emotion)
        
    # --- Step 6: Clean and Return Response ---
        cleaned_response = clean_ai_response.clean_ai_response(raw_response)
        print("cleaned response before ",cleaned_response)
        
        # Add metadata about which provider was used
        if hasattr(cleaned_response, 'answerDetails') and cleaned_response.answerDetails is not None and hasattr(cleaned_response.answerDetails, 'additional_info'):
            cleaned_response.answerDetails.additional_info['provider_used'] = provider_used.value
        print("cleaned response",cleaned_response)
        return cleaned_response
    
    except Exception as e:
        logger.error(f"❌ Chat service error: {e}", exc_info=True)
        error_message = str(e) if str(e) else "Sorry, I'm having trouble processing your request."
        return _create_error_response(error_message, "neutral", query)

    

def _create_error_response(message: str, emotion: str, query: str = ""):
    """Helper to create fallback error responses with all required fields."""
    from app.schemas.chat_schema import ChatResponse, ActionDetails, Confirmation, AnswerDetails
    
    return ChatResponse(
        userQuery=query,  # ✅ Added missing field
        answer=message,
        answerEnglish=message,  # ✅ Added missing field (same as answer for errors)
        actionCompletedMessage="",  # ✅ Added missing field (empty for errors)
        actionCompletedMessageEnglish="",  # ✅ Added missing field (empty for errors)
        action="",
        emotion=emotion,
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
            searchResults=[],  # Make sure this is also in your schema
            confirmation=Confirmation(isConfirmed=False, actionRegardingQuestion=""),
            additional_info={}
        )
    )