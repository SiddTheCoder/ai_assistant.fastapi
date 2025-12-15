import redis.asyncio as redis
from redis import exceptions as redis_exceptions
import json
from typing import Any, Optional, List, Dict
from datetime import datetime, timezone, timedelta
import numpy as np
import hashlib
import logging

logger = logging.getLogger(__name__)

NEPAL_TZ = timezone(timedelta(hours=5, minutes=45))

# Async Redis client - type hint properly
redis_client: redis.Redis = redis.Redis(
    host='localhost', 
    port=6379, 
    db=0, 
    decode_responses=True, 
    socket_connect_timeout=3, 
    socket_timeout=3
)

def safe_warn(msg: str) -> None:
    """Print lightweight non-blocking warnings."""
    print(f"[Redis Warning] {msg}")

# ============ GENERIC CACHE (USER-SCOPED) ============

async def set_cache(user_id: str, key: str, value: Any, expire: Optional[int] = None) -> None:
    """Set a value in the Redis cache."""
    try:
        full_key = f"user:{user_id}:cache:{key}"
        await redis_client.set(full_key, json.dumps(value), ex=expire)
    except Exception as e:
        safe_warn(f"Failed to set cache for key '{key}': {e}")

async def get_cache(user_id: str, key: str) -> Optional[Any]:
    """Get a value from the Redis cache."""
    try:
        full_key = f"user:{user_id}:cache:{key}"
        value = await redis_client.get(full_key)
        if value:
            return json.loads(value)
    except Exception as e:
        safe_warn(f"Failed to get cache for key '{key}': {e}")
    return None

async def delete_cache(user_id: str, key: str) -> None:
    """Delete a value from the Redis cache."""
    try:
        full_key = f"user:{user_id}:cache:{key}"
        await redis_client.delete(full_key)
    except Exception as e:
        safe_warn(f"Failed to delete cache for key '{key}': {e}")

async def clear_cache(user_id: str) -> None:
    """Clear all cache for a user."""
    try:
        pattern = f"user:{user_id}:cache:*"
        cursor = 0
        while True:
            cursor, keys = await redis_client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception as e:
        safe_warn(f"Failed to clear cache for user '{user_id}': {e}")

# ============ CONVERSATION HISTORY ============

async def add_message(user_id: str, role: str, content: str) -> None:
    """
    Add a message to the conversation history.
    
    Args:
        user_id: User identifier
        role: Either 'user' or 'assistant'
        content: The message content
    """
    try:
        key = f"user:{user_id}:conversation"
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(NEPAL_TZ).isoformat()
        }
        await redis_client.rpush(key, json.dumps(message)) # type: ignore
        
        # Cache embedding in background
        import asyncio
        asyncio.create_task(_cache_embedding_with_user(content, user_id))
            
    except Exception as e:
        safe_warn(f"Failed to add message for user '{user_id}': {e}")


async def _cache_embedding_with_user(text: str, user_id: str) -> None:
    """Background task to cache embedding with user tracking"""
    try:
        from app.services.embedding_services import embedding_service
        embedding = await embedding_service.embed_single(text)
        await _set_embedding_cache(user_id, text, embedding)
    except Exception as e:
        logger.debug(f"Failed to cache embedding: {e}")


async def get_last_n_messages(user_id: str, n: int = 10) -> List[Dict[str, Any]]:
    """
    Get the last N messages from conversation history.
    
    Args:
        user_id: User identifier
        n: Number of recent messages to retrieve
        
    Returns:
        List of message dictionaries with 'role' and 'content' keys
    """
    try:
        key = f"user:{user_id}:conversation"
        messages_raw: List[bytes] = await redis_client.lrange(key, -n, -1)  # type: ignore
        if not messages_raw:
            return []
        
        messages: List[Dict[str, Any]] = []
        for msg in messages_raw:
            if msg:
                try:
                    messages.append(json.loads(msg))
                except json.JSONDecodeError:
                    continue
        
        return messages[::-1]  # newest first
    except redis_exceptions.TimeoutError:
        safe_warn(f"Redis timed out while fetching messages for user '{user_id}'")
        return []
    except redis_exceptions.ConnectionError:
        safe_warn(f"Cannot connect to Redis for user '{user_id}'")
        return []
    except Exception as e:
        safe_warn(f"Failed to get messages for user '{user_id}': {e}")
        return []


async def clear_conversation_history(user_id: str) -> None:
    """Clear all conversation history for a user."""
    try:
        key = f"user:{user_id}:conversation"
        await redis_client.delete(key)
    except Exception as e:
        safe_warn(f"Failed to clear conversation history for user '{user_id}': {e}")


# ============ EMBEDDING CACHE ============

EMBEDDING_TTL = 86400 * 7  # 7 days

def _get_text_hash(text: str) -> str:
    """Generate hash for text"""
    return hashlib.md5(text.encode()).hexdigest()

async def _get_embedding_cache(user_id: str, text: str) -> Optional[List[float]]:
    """Get cached embedding for text"""
    try:
        text_hash = _get_text_hash(text)
        cache_key = f"user:{user_id}:emb:{text_hash}"
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        return None
    except Exception as e:
        logger.debug(f"Failed to get cached embedding: {e}")
        return None

async def _set_embedding_cache(user_id: str, text: str, embedding: List[float]) -> bool:
    """Cache an embedding"""
    try:
        text_hash = _get_text_hash(text)
        cache_key = f"user:{user_id}:emb:{text_hash}"
        await redis_client.setex(cache_key, EMBEDDING_TTL, json.dumps(embedding))
        return True
    except Exception as e:
        logger.debug(f"Failed to cache embedding: {e}")
        return False


async def get_embeddings_for_messages(
    user_id: str,
    messages: List[Dict[str, str]],
    text_key: str = "content"
) -> List[List[float]]:
    """
    Get embeddings for messages with caching
    
    Args:
        user_id: User identifier
        messages: List of message dicts
        text_key: Key containing text
        
    Returns:
        List of embeddings (same order as input)
    """
    from app.services.embedding_services import embedding_service
    
    embeddings: List[Optional[List[float]]] = []
    texts_to_compute: List[str] = []
    compute_indices: List[int] = []
    
    # Check cache for each message
    for i, msg in enumerate(messages):
        text = msg.get(text_key, "")
        cached = await _get_embedding_cache(user_id, text)
        
        if cached:
            embeddings.append(cached)
        else:
            embeddings.append(None)
            texts_to_compute.append(text)
            compute_indices.append(i)
    
    # Compute missing embeddings
    if texts_to_compute:
        logger.info(f"🔄 Computing {len(texts_to_compute)} embeddings (cache misses)")
        new_embeddings = await embedding_service.embed_batch(texts_to_compute)
        
        # Cache and insert
        for idx, text, embedding in zip(compute_indices, texts_to_compute, new_embeddings):
            embeddings[idx] = embedding
            await _set_embedding_cache(user_id, text, embedding)
    
    cache_hits = len(messages) - len(texts_to_compute)
    if messages:
        logger.info(f"📊 Cache: {cache_hits}/{len(messages)} hits ({cache_hits/len(messages)*100:.0f}%)")
    
    # Filter out None values
    result: List[List[float]] = []
    for emb in embeddings:
        if emb is not None:
            result.append(emb)
    
    return result


async def semantic_search_messages(
    user_id: str,
    query: str,
    n: int = 500,
    top_k: int = 10,
    threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Ultra-fast semantic search using cached embeddings
    
    Args:
        user_id: User ID
        query: Search query
        n: Number of recent messages to search
        top_k: Number of results
        threshold: Minimum similarity
        
    Returns:
        Top matching messages with scores
    """
    import time
    start = time.time()
    
    # Get messages
    messages = await get_last_n_messages(user_id, n)
    if not messages:
        return []
    
    logger.info(f"🔍 Searching {len(messages)} messages for '{query[:50]}...'")
    
    # Get query embedding
    query_embeddings = await get_embeddings_for_messages(user_id, [{"content": query}])
    query_emb = np.array(query_embeddings[0])
    
    # Get message embeddings (CACHED!)
    msg_embeddings = await get_embeddings_for_messages(user_id, messages, "content")
    msg_embs = np.array(msg_embeddings)
    
    # Calculate similarities
    similarities = np.dot(msg_embs, query_emb) / (
        np.linalg.norm(msg_embs, axis=1) * np.linalg.norm(query_emb)
    )
    
    # Filter and sort
    results: List[Dict[str, Any]] = []
    for idx, (msg, score) in enumerate(zip(messages, similarities)):
        if score >= threshold:
            result = msg.copy()
            result["_similarity_score"] = float(round(float(score), 4))
            results.append(result)
    
    results.sort(key=lambda x: x["_similarity_score"], reverse=True)
    
    # Add ranks
    for rank, result in enumerate(results[:top_k], 1):
        result["_rank"] = rank
    
    elapsed = time.time() - start
    logger.info(f"⚡ Search completed in {elapsed*1000:.0f}ms")
    
    return results[:top_k]


async def warm_embedding_cache(user_id: str, n: int = 500) -> int:
    """
    Pre-compute and cache embeddings for user's messages
    
    Args:
        user_id: User ID
        n: Number of messages to cache
        
    Returns:
        Number of embeddings cached
    """
    logger.info(f"🔥 Warming cache for user {user_id}: {n} messages")
    
    messages = await get_last_n_messages(user_id, n)
    if not messages:
        return 0
    
    await get_embeddings_for_messages(user_id, messages, "content")
    
    logger.info(f"✅ Cache warmed: {len(messages)} messages")
    return len(messages)


async def get_embedding_cache_stats(user_id: str) -> Dict[str, Any]:
    """Get cache statistics for a user"""
    try:
        pattern = f"user:{user_id}:emb:*"
        cursor = 0
        keys_list: List[str] = []
        
        while True:
            cursor, keys = await redis_client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                keys_list.extend(keys)
            if cursor == 0:
                break
        
        # Sample for memory estimation
        total_size = 0
        if keys_list:
            sample_keys = keys_list[:min(10, len(keys_list))]
            for key in sample_keys:
                val = await redis_client.get(key)
                if val:
                    total_size += len(val)
            
            avg_size = total_size / len(sample_keys) if sample_keys else 0
            estimated_total = avg_size * len(keys_list)
        else:
            estimated_total = 0
        
        return {
            "total_cached": len(keys_list),
            "estimated_memory_mb": estimated_total / (1024 * 1024),
            "ttl_days": EMBEDDING_TTL / 86400
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {}


async def clear_embedding_cache(user_id: str) -> int:
    """Clear all cached embeddings for a user"""
    try:
        pattern = f"user:{user_id}:emb:*"
        cursor = 0
        total_deleted = 0
        
        while True:
            cursor, keys = await redis_client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await redis_client.delete(*keys)
                total_deleted += len(keys)
            if cursor == 0:
                break
        
        if total_deleted > 0:
            logger.info(f"🗑️  Cleared {total_deleted} cached embeddings")
        
        return total_deleted
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return 0


# ============ USER DETAILS ==============

async def set_user_details(user_id: str, details: Dict[str, Any]) -> None:
    """Set user details"""
    try:
        key = f"user:{user_id}:details"
        await redis_client.set(key, json.dumps(details))
    except Exception as e:
        safe_warn(f"Failed to set user details for user '{user_id}': {e}")

async def get_user_details(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user details"""
    try:
        key = f"user:{user_id}:details"
        details = await redis_client.get(key)
        if details:
            return json.loads(details)
    except Exception as e:
        safe_warn(f"Failed to get user details for user '{user_id}': {e}")
    return None

async def clear_user_details(user_id: str) -> None:
    """Clear user details"""
    try:
        key = f"user:{user_id}:details"
        await redis_client.delete(key)
    except Exception as e:
        safe_warn(f"Failed to clear user details for user '{user_id}': {e}")

async def override_user_details(user_id: str, details: Dict[str, Any]) -> None:
    """Override user details completely"""
    try:
        await set_user_details(user_id, details)
    except Exception as e:
        safe_warn(f"Failed to override user details for user '{user_id}': {e}")

async def update_user_details(user_id: str, details: Dict[str, Any]) -> None:
    """Update user details (merge with existing)"""
    try:
        existing_details = await get_user_details(user_id)
        if existing_details is None:
            await set_user_details(user_id, details)
        else:
            existing_details.update(details)
            await set_user_details(user_id, existing_details)
    except Exception as e:
        safe_warn(f"Failed to update user details for user '{user_id}': {e}")

# ============ HYBRID USAGE ===============
#TODO
async def process_query_and_get_context(user_id: str, current_query: str) -> tuple[List[Dict[str, Any]], bool]:
    """
    app.cache.redis.config
    this function checks whether pinecone data is needed or not if yeah then pinecone data is returned or local data
    """
    is_pinecone_needed = False
    # Step 1: Get recent context from Redis
    context = await semantic_search_messages(user_id, current_query)
    await _append_message_to_local_and_cloud(user_id, current_query)
    
    # If Redis context is empty, fetch from Pinecone
    if not context or len(context) == 0:
        #TODO WebSocket emit a message as loading your memory
        from app.db.pinecone import config as pinecone_config
        print("[Debug] Low similarity - fetching from Pinecone")
        context = pinecone_config.get_user_all_queries(user_id) # Fetch from Pinecone
        is_pinecone_needed = True
        return context, is_pinecone_needed

    print("[Debug] High similarity - using only Redis context")
    return context, is_pinecone_needed

async def _append_message_to_local_and_cloud(user_id, current_query):
    await add_message(user_id, "user", current_query)
    # from app.db.pinecone.config import upsert_query
    # upsert_query(user_id, current_query)

# ============ USER MANAGEMENT ============

async def clear_all_user_data(user_id: str) -> None:
    """Clear ALL data for a user (conversation, cache, embeddings, details)"""
    try:
        pattern = f"user:{user_id}:*"
        cursor = 0
        total_deleted = 0
        
        while True:
            cursor, keys = await redis_client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await redis_client.delete(*keys)
                total_deleted += len(keys)
            if cursor == 0:
                break
        
        if total_deleted > 0:
            logger.info(f"🗑️  Cleared all data for user {user_id}: {total_deleted} keys")
    except Exception as e:
        safe_warn(f"Failed to clear all data for user '{user_id}': {e}")