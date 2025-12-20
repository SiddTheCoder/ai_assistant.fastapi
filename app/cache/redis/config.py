import redis.asyncio as redis
from redis import exceptions as redis_exceptions
import json
from typing import Any, Optional, List, Dict, Tuple
from datetime import datetime, timezone, timedelta
from app.db.pinecone.config import upsert_query
import numpy as np
import hashlib
import logging
import asyncio
import time

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


# ============ OPTIMIZED EMBEDDING CACHE ============

EMBEDDING_TTL = 86400 * 7  # 7 days

def _get_text_hash(text: str) -> str:
    """Generate hash for text"""
    return hashlib.md5(text.encode()).hexdigest()


async def _get_embedding_cache(user_id: str, text: str) -> Optional[List[float]]:
    """Get cached embedding for text (single)"""
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


async def _batch_get_embedding_cache(
    user_id: str, 
    texts: List[str]
) -> List[Optional[List[float]]]:
    """
    OPTIMIZATION: Batch cache retrieval using Redis pipeline
    Single network round-trip instead of N calls
    """
    if not texts:
        return []
    
    try:
        # Build all cache keys
        cache_keys = [
            f"user:{user_id}:emb:{_get_text_hash(text)}" 
            for text in texts
        ]
        
        # Use pipeline for batch get
        pipeline = redis_client.pipeline()
        for key in cache_keys:
            pipeline.get(key)
        
        cached_values = await pipeline.execute()
        
        # Parse results
        results: List[Optional[List[float]]] = []
        for cached in cached_values:
            if cached:
                results.append(json.loads(cached))
            else:
                results.append(None)
        
        return results
    except Exception as e:
        logger.debug(f"Failed to batch get cached embeddings: {e}")
        return [None] * len(texts)


async def _set_embedding_cache(user_id: str, text: str, embedding: List[float]) -> bool:
    """Cache an embedding (single)"""
    try:
        text_hash = _get_text_hash(text)
        cache_key = f"user:{user_id}:emb:{text_hash}"
        await redis_client.setex(cache_key, EMBEDDING_TTL, json.dumps(embedding))
        return True
    except Exception as e:
        logger.debug(f"Failed to cache embedding: {e}")
        return False


async def _batch_set_embedding_cache(
    user_id: str,
    texts: List[str],
    embeddings: List[List[float]]
) -> bool:
    """
    OPTIMIZATION: Batch cache setting using Redis pipeline
    Single network round-trip instead of N calls
    """
    if not texts or not embeddings or len(texts) != len(embeddings):
        return False
    
    try:
        pipeline = redis_client.pipeline()
        
        for text, embedding in zip(texts, embeddings):
            text_hash = _get_text_hash(text)
            cache_key = f"user:{user_id}:emb:{text_hash}"
            pipeline.setex(cache_key, EMBEDDING_TTL, json.dumps(embedding))
        
        await pipeline.execute()
        return True
    except Exception as e:
        logger.debug(f"Failed to batch cache embeddings: {e}")
        return False


def _fast_cosine_similarity(query_emb: np.ndarray, doc_embs: np.ndarray) -> np.ndarray:
    """
    OPTIMIZATION: Faster cosine similarity with pre-normalized vectors
    """
    # Normalize vectors
    query_norm = query_emb / np.linalg.norm(query_emb)
    doc_norms = doc_embs / np.linalg.norm(doc_embs, axis=1, keepdims=True)
    
    # Matrix multiplication for similarity (fastest method)
    similarities = doc_norms @ query_norm
    
    return similarities


async def get_embeddings_for_messages(
    user_id: str,
    messages: List[Dict[str, str]],
    text_key: str = "content"
) -> List[List[float]]:
    """
    OPTIMIZED: Get embeddings for messages with batch caching
    
    Args:
        user_id: User identifier
        messages: List of message dicts
        text_key: Key containing text
        
    Returns:
        List of embeddings (same order as input)
    """
    from app.services.embedding_services import embedding_service
    
    if not messages:
        return []
    
    texts = [msg.get(text_key, "") for msg in messages]
    
    # OPTIMIZATION: Batch cache lookup (1 network call instead of N)
    cached_embeddings = await _batch_get_embedding_cache(user_id, texts)
    
    embeddings: List[Optional[List[float]]] = []
    texts_to_compute: List[str] = []
    compute_indices: List[int] = []
    
    for i, (text, cached) in enumerate(zip(texts, cached_embeddings)):
        if cached:
            embeddings.append(cached)
        else:
            embeddings.append(None)
            texts_to_compute.append(text)
            compute_indices.append(i)
    
    # Compute missing embeddings in batch
    if texts_to_compute:
        logger.info(f"🔄 Computing {len(texts_to_compute)} embeddings (cache misses)")
        compute_start = time.time()
        
        new_embeddings = await embedding_service.embed_batch(texts_to_compute)
        
        compute_elapsed = (time.time() - compute_start) * 1000
        logger.info(f"⚡ Embedded {len(texts_to_compute)} texts in {compute_elapsed:.0f}ms")
        
        # Insert computed embeddings
        for idx, embedding in zip(compute_indices, new_embeddings):
            embeddings[idx] = embedding
        
        # OPTIMIZATION: Batch cache (1 network call instead of N)
        await _batch_set_embedding_cache(user_id, texts_to_compute, new_embeddings)
    
    # Log cache stats
    cache_hits = len(messages) - len(texts_to_compute)
    if messages:
        hit_rate = (cache_hits / len(messages)) * 100
        logger.info(f"📊 Cache: {cache_hits}/{len(messages)} hits ({hit_rate:.0f}%)")
    
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
    ULTRA-OPTIMIZED: Semantic search with parallel execution and batch operations
    
    Args:
        user_id: User ID
        query: Search query
        n: Number of recent messages to search
        top_k: Number of results
        threshold: Minimum similarity
        
    Returns:
        Top matching messages with scores
    """
    start = time.time()
    
    # Get messages
    messages = await get_last_n_messages(user_id, n)
    if not messages:
        return []
    
    logger.info(f"🔍 Searching {len(messages)} messages for '{query[:50]}...'")
    
    # OPTIMIZATION: Parallel execution - get query + message embeddings simultaneously
    query_task = asyncio.create_task(
        get_embeddings_for_messages(user_id, [{"content": query}], "content")
    )
    messages_task = asyncio.create_task(
        get_embeddings_for_messages(user_id, messages, "content")
    )
    
    # Wait for both to complete
    query_embeddings, msg_embeddings = await asyncio.gather(query_task, messages_task)
    
    if not query_embeddings or not msg_embeddings:
        return []
    
    query_emb = np.array(query_embeddings[0])
    msg_embs = np.array(msg_embeddings)
    
    # OPTIMIZATION: Fast cosine similarity
    similarities = _fast_cosine_similarity(query_emb, msg_embs)
    
    # Filter and build results
    results: List[Dict[str, Any]] = []
    for idx, (msg, score) in enumerate(zip(messages, similarities)):
        if score >= threshold:
            result = msg.copy()
            result["_similarity_score"] = float(round(float(score), 4))
            results.append(result)
    
    # Sort by score
    results.sort(key=lambda x: x["_similarity_score"], reverse=True)
    
    # Add ranks
    for rank, result in enumerate(results[:top_k], 1):
        result["_rank"] = rank
    
    elapsed = (time.time() - start) * 1000
    logger.info(f"⚡ Search completed in {elapsed:.0f}ms ({len(results)} matches)")
    
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


# ============ HYBRID USAGE ===============

async def process_query_and_get_context(user_id: str, current_query: str) -> tuple[List[Dict[str, Any]], bool]:
    """
    OPTIMIZED: Check if Pinecone data is needed, with parallel operations
    
    This function checks whether pinecone data is needed or not. 
    If yes, pinecone data is returned; otherwise local data is used.
    """
    is_pinecone_needed = False
    
    # OPTIMIZATION: Run semantic search and message appending in parallel
    search_task = asyncio.create_task(
        semantic_search_messages(user_id, current_query)
    )
    append_task = asyncio.create_task(
        _append_message_to_local_and_cloud(user_id, current_query)
    )
    
    # Wait for search to complete (append runs in background)
    context = await search_task
    await append_task  # Ensure append completes
    
    # If Redis context is empty, fetch from Pinecone
    if not context or len(context) == 0:
        from app.db.pinecone import config as pinecone_config
        logger.info("[Pinecone] Low similarity - fetching from Pinecone")
        context = pinecone_config.get_user_all_queries(user_id)
        is_pinecone_needed = True
        return context, is_pinecone_needed

    logger.info(f"[Redis] High similarity - using Redis context ({len(context)} results)")
    return context, is_pinecone_needed


async def _append_message_to_local_and_cloud(user_id: str, current_query: str):
    """Append message to local Redis and cloud Pinecone"""
    await add_message(user_id, "user", current_query)

    # Upsert to Pinecone in background
    asyncio.create_task(
        asyncio.to_thread(upsert_query, user_id, current_query)
    )


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

# ============ USER MANAGEMENT ============

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