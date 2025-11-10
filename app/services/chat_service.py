from app.utils import openrouter_config, clean_ai_response
from app.config import settings
from app.services.detect_emotion import detect_emotion
from app.services.actions.action_dispatcher import dispatch_action
from app.libs.tts.speak import speak,speak_background
from app.db.pinecone.config import (get_user_all_queries,search_user_queries)
from app.cache.redis.config import get_last_n_messages,process_query_and_get_context
from app.utils.build_prompt import format_context,build_prompt
import logging

logger = logging.getLogger(__name__)

async def chat(query: str, model_name: str = settings.first_model_name, user_id:str = "user_1"):
    """
    Main chat handler with optimized prompt and error handling.
    """
    if not query or not query.strip():
        return _create_error_response("Empty query received", "neutral")
    
    # Get context via query
    query_context, is_pinecone_needed = process_query_and_get_context(user_id, query, search_user_queries, get_user_all_queries, threshold=0.2)
    import json
    logger.info(f"Query context from chat_service: {json.dumps(query_context, indent=2)}")

    # Get Local Context from redis
    local_context = get_last_n_messages(user_id, n=20)
    logger.info(f"Query context from chat_service: {json.dumps(local_context, indent=2)}")

    # Detect emotion
    # emotion = await detect_emotion(text)
    emotion = "neutral"  

    # Build Prompt using context
    prompt = build_prompt(emotion, query, local_context, query_context)

    # Step 3: Call OpenRouter API
    try:
        completion = openrouter_config.client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://siddhantyadav.com.np",
                "X-Title": "Siddy Coddy",
            },
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            # max_tokens=4000
        )

        raw_response = completion.choices[0].message.content
        logger.info(f"Raw AI response: {raw_response}...")
        
        if not raw_response:
            return _create_error_response("Empty AI response", emotion)
        
    # Step 4: Clean and validate AI response
        cleaned_res = clean_ai_response.clean_ai_response(raw_response)

    # Step 5: Decide and dispatch action if needed
        if(cleaned_res):
            final_data = decide_action(cleaned_res)
            if(final_data): # type: ignore
              logger.info(f"Final response from chat_service: {final_data}...")
              return final_data
            else:
              logger.info(f"Final response from chat_service: {cleaned_res}...")
              return cleaned_res

    except Exception as e:
        logger.error(f"OpenRouter request failed: {e}", exc_info=True)
        return _create_error_response(
            "Sorry, I'm having trouble reaching the AI server right now.", 
            emotion
        )

""" """    
    
#TODO : Frontend will handle all the action dispatching and confirmation
#TODO # later on this will only return the res and all action will be handled in the electron local devices
# Function to decide and dispatch action in a separate thread
def decide_action(details):
    if(details.action == ""):
        # speak_background(details.answer, speed=1)
        # if(details.answerDetails.content != ""):
        #     speak_background(details.answerDetails.content, speed=1)
        return details
    if(details.action != "" and details.actionDetails.confirmation.isConfirmed == False):
        # speak_background(details.actionDetails.confirmation.actionRegardingQuestion, speed=1)
        return details
    if(details.action != "" and details.actionDetails.confirmation.isConfirmed == True):
        from app.utils.run_action_in_thread import run_action_in_thread
        # speak_background(details.answer, speed=1)
        data = run_action_in_thread(details.actionDetails.type, details)
        return data


def _create_error_response(message: str, emotion: str):
    """Helper to create fallback error responses."""
    from app.schemas.chat_schema import ChatResponse, ActionDetails, Confirmation, AnswerDetails
    
    return ChatResponse(
        answer=message,
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
            confirmation=Confirmation(isConfirmed=False, actionRegardingQuestion=""),
            additional_info={}
        )
    )