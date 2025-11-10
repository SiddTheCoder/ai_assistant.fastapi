import redis
import json
from typing import Any, Optional, List, Dict, cast, Union
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from app.utils.build_prompt import format_context

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def safe_warn(msg: str) -> None:
    """Print lightweight non-blocking warnings."""
    print(f"[Redis Warning] {msg}")

def set_cache(key: str, value: Any, expire: Optional[int] = None) -> None:
    """Set a value in the Redis cache."""
    try:
        redis_client.set(key, json.dumps(value), ex=expire)
    except Exception as e:
        safe_warn(f"Failed to set cache for key '{key}': {e}")

def get_cache(key: str) -> Optional[Any]:
    """Get a value from the Redis cache."""
    try:
        value = redis_client.get(key)
        if value is not None:
            return json.loads(cast(Union[str, bytes, bytearray], value))
    except Exception as e:
        safe_warn(f"Failed to get cache for key '{key}': {e}")
    return None

def delete_cache(key: str) -> None:
    """Delete a value from the Redis cache."""
    try:
        redis_client.delete(key)
    except Exception as e:
        safe_warn(f"Failed to delete cache for key '{key}': {e}")

def clear_cache() -> None:
    """Clear the Redis cache."""
    try:
        redis_client.flushdb()
    except Exception as e:
        safe_warn(f"Failed to clear Redis cache: {e}")

# ============ NEW CONVERSATION HISTORY FUNCTIONS ============

def add_message(user_id: str, role: str, content: str) -> None:
    """
    Add a message to the conversation history.
    
    Args:
        user_id: User identifier
        role: Either 'user' or 'assistant'
        content: The message content
    """
    try:
        key = f"conversation:{user_id}"
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        redis_client.rpush(key, json.dumps(message))
    except Exception as e:
        safe_warn(f"Failed to add message for user '{user_id}': {e}")


def get_last_n_messages(user_id: str, n: int = 20) -> List[Dict[str, str]]:
    """
    Get the last N messages from conversation history.
    
    Args:
        user_id: User identifier
        n: Number of recent messages to retrieve
        
    Returns:
        List of message dictionaries with 'role' and 'content' keys
    """
    try:
        key = f"conversation:{user_id}"
        # Get last n messages (Redis uses -n to get last n items)
        messages_raw = redis_client.lrange(key, -n, -1)
        # Explicitly handle the return type
        if messages_raw is None:
            return []
        # Convert to list and parse JSON
        messages_list = list(messages_raw) if not isinstance(messages_raw, list) else messages_raw # type: ignore
        return [json.loads(msg) for msg in messages_list if msg]
    except Exception as e:
        safe_warn(f"Failed to get messages for user '{user_id}': {e}")
        return []


def clear_conversation_history(user_id: str) -> None:
    """Clear all conversation history for a user."""
    try:
        key = f"conversation:{user_id}"
        redis_client.delete(key)
    except Exception as e:
        safe_warn(f"Failed to clear conversation history for user '{user_id}': {e}")


def compute_similarity(current_query: str, last_context: List[Dict[str, str]], 
                      method: str = "tfidf",
                      focus_on_user_messages: bool = True) -> float:
    """
    Compute similarity between current query and recent conversation context.
    
    Args:
        current_query: The current user query
        last_context: List of recent messages from Redis
        method: Similarity method ('tfidf', 'jaccard', or 'simple')
        focus_on_user_messages: If True, only compare with user messages (ignore assistant)
        
    Returns:
        Similarity score between 0 and 1
    """
    if not last_context:
        return 0.0
    
    # Filter messages if needed
    if focus_on_user_messages:
        relevant_messages = [msg for msg in last_context if msg.get("role") == "user"]
    else:
        relevant_messages = last_context
    
    if not relevant_messages:
        return 0.0
    
    # Combine context messages into a single string
    context_text = " ".join([msg.get("content", "") for msg in relevant_messages])
    
    if not context_text.strip():
        return 0.0
    
    if method == "tfidf":
        return _tfidf_similarity(current_query, context_text)
    elif method == "jaccard":
        return _jaccard_similarity(current_query, context_text)
    else:
        return _simple_overlap_similarity(current_query, context_text)


def _tfidf_similarity(query: str, context: str) -> float:
    """Compute TF-IDF based cosine similarity."""
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        vectors = vectorizer.fit_transform([query, context])
        # Convert sparse matrix to dense array for indexing
        similarity = cosine_similarity(vectors[0:1], vectors[1:2]) # type: ignore
        return float(similarity[0, 0])
    except Exception as e:
        safe_warn(f"TF-IDF similarity computation failed: {e}")
        return 0.0


def _jaccard_similarity(query: str, context: str) -> float:
    """Compute Jaccard similarity between word sets."""
    query_words = set(query.lower().split())
    context_words = set(context.lower().split())
    
    if not query_words or not context_words:
        return 0.0
    
    intersection = query_words.intersection(context_words)
    union = query_words.union(context_words)
    
    return len(intersection) / len(union) if union else 0.0


def _simple_overlap_similarity(query: str, context: str) -> float:
    """Simple word overlap ratio."""
    query_words = set(query.lower().split())
    context_words = set(context.lower().split())
    
    if not query_words:
        return 0.0
    
    overlap = query_words.intersection(context_words)
    return len(overlap) / len(query_words)

# ============ USAGE EXAMPLE ============

def process_query_and_get_context(user_id: str, current_query: str, 
                                      pinecone_search_func, 
                                      pinecone_get_func,
                                      threshold: float = 0.3):
    
    """
    this function checks whether pinecone data is needed or not if yeah then pinecone data is returned or local data
    """
    is_pinecone_needed = False
    # Step 1: Get recent context from Redis
    local_context = get_last_n_messages(user_id, n=20)
    
    # If Redis context is empty, fetch from Pinecone
    if not local_context:
        local_context = pinecone_get_func(user_id) # Fetch from Pinecone
        for context in local_context:
            add_message(user_id, "user", context.get("query", ""))
        is_pinecone_needed = True
        return local_context, is_pinecone_needed

    # Step 2: Compute similarity with recent context
    similarity = compute_similarity(current_query, local_context)
    print(f"[Debug] Similarity score: {similarity:.3f}, Threshold: {threshold}")
    
    is_pinecone_needed = similarity < threshold
    # Step 3: Decide whether to use Pinecone for long-term context
    if is_pinecone_needed:
        print("[Debug] Low similarity - fetching from Pinecone")
        query_based_context = pinecone_search_func(user_id, current_query)
        return query_based_context, is_pinecone_needed
    else:
        print("[Debug] High similarity - using only Redis context")
        return local_context, is_pinecone_needed
   

def build_prompt(current_query: str, context: List[Dict[str, str]]) -> str:
    """
    Build a prompt with context for the LLM.
    
    Args:
        current_query: Current user query
        context: List of context messages
        
    Returns:
        Formatted prompt string
    """
    prompt = "Previous conversation:\n"
    for msg in context:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        prompt += f"{role.capitalize()}: {content}\n"
    
    prompt += f"\nCurrent query: {current_query}\n\nResponse:"
    return prompt