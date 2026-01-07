"""
Redis Manager with Singleton Pattern
Auto-switches between local Redis (dev) and Upstash (production)
"""
import redis.asyncio as redis
from upstash_redis.asyncio import Redis as UpstashRedis
from redis import exceptions as redis_exceptions
import json
from typing import Any, Optional, List, Dict, Union, Protocol
from datetime import datetime, timezone, timedelta
from app.config import settings
import numpy as np
import hashlib
import logging
import asyncio
import time

logger = logging.getLogger(__name__)

NEPAL_TZ = timezone(timedelta(hours=5, minutes=45))
EMBEDDING_TTL = 86400 * 7  # 7 days


class RedisPipeline(Protocol):
    """Protocol for Redis pipeline operations"""
    def get(self, key: str) -> Any: ...
    def setex(self, key: str, seconds: int, value: str) -> Any: ...
    async def execute(self) -> List[Any]: ...


class RedisManager:
    """
    Singleton Redis Manager
    - Auto-detects environment (dev/prod)
    - Uses local Docker Redis for development
    - Uses Upstash Redis for production
    - All operations are async and non-blocking
    """
    
    _instance: Optional['RedisManager'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize only once (singleton pattern)"""
        if self._initialized:
            return
            
        self._initialized = True
        self.client: Union[redis.Redis, UpstashRedis, None] = None  # type: ignore
        self._is_upstash = False
        self._init_lock = asyncio.Lock()
        self._init_started = False
    
    async def _async_init(self):
        """Async initialization - lazy loaded on first use"""
        try:
            # Determine environment and initialize appropriate client
            if settings.environment == "production":
                await self._init_upstash()
            else:
                await self._init_local_redis()
                
            logger.info(f"✅ Redis initialized: {'Upstash' if self._is_upstash else 'Local Docker'}")
        except Exception as e:
            logger.error(f"❌ Redis initialization failed: {e}")
            self.client = None
            raise
    
    async def initialize(self):
        """Manually initialize the Redis client (optional)"""
        await self._ensure_client()
    
    async def _init_upstash(self):
        """Initialize Upstash Redis for production"""
        try:
            self.client = UpstashRedis(
                url=settings.upstash_redis_rest_url,
                token=settings.upstash_redis_rest_token,
            )
            self._is_upstash = True
            
            # Test connection
            await self.client.ping()  # type: ignore
            logger.info("🌐 Connected to Upstash Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Upstash: {e}")
            raise
    
    async def _init_local_redis(self):
        """Initialize local Docker Redis for development"""
        try:
            self.client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3
            )
            self._is_upstash = False
            
            # Test connection
            await self.client.ping()  # type: ignore
            logger.info("🐳 Connected to Local Docker Redis")
        except Exception as e:
            logger.error(f"Failed to connect to local Redis: {e}")
            raise
    
    async def _ensure_client(self):
        """Ensure client is initialized before operations"""
        if self.client is not None:
            return
        
        # Use lock to prevent multiple initializations
        async with self._init_lock:
            # Double-check after acquiring lock
            if self.client is not None:
                return
            
            if not self._init_started:
                self._init_started = True
                await self._async_init()
    
    def _safe_warn(self, msg: str):
        """Print lightweight non-blocking warnings"""
        print(f"[Redis Warning] {msg}")
    
    # ============ CORE REDIS OPERATIONS ============
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set a value in Redis"""
        try:
            await self._ensure_client()
            if self._is_upstash:
                await self.client.set(key, value, ex=ex)  # type: ignore
            else:
                await self.client.set(key, value, ex=ex)  # type: ignore
            return True
        except Exception as e:
            self._safe_warn(f"Failed to set key '{key}': {e}")
            return False
    
    async def get(self, key: str) -> Optional[str]:
        """Get a value from Redis"""
        try:
            await self._ensure_client()
            result = await self.client.get(key)  # type: ignore
            return result
        except Exception as e:
            self._safe_warn(f"Failed to get key '{key}': {e}")
            return None
    
    async def delete(self, *keys: str) -> bool:
        """Delete one or more keys"""
        try:
            await self._ensure_client()
            await self.client.delete(*keys)  # type: ignore
            return True
        except Exception as e:
            self._safe_warn(f"Failed to delete keys: {e}")
            return False
    
    async def rpush(self, key: str, *values: str) -> bool:
        """Push values to the end of a list"""
        try:
            await self._ensure_client()
            await self.client.rpush(key, *values)  # type: ignore
            return True
        except Exception as e:
            self._safe_warn(f"Failed to rpush to '{key}': {e}")
            return False
    
    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get a range of elements from a list"""
        try:
            await self._ensure_client()
            result = await self.client.lrange(key, start, end)  # type: ignore
            if result is None:
                return []
            # Handle both list and bytes responses
            if isinstance(result, list):
                return [str(item) if item else "" for item in result]
            return []
        except Exception as e:
            self._safe_warn(f"Failed to lrange '{key}': {e}")
            return []
    
    async def scan(self, cursor: int = 0, match: Optional[str] = None, count: int = 100) -> tuple[int, List[str]]:
        """Scan for keys matching a pattern"""
        try:
            await self._ensure_client()
            
            if self._is_upstash:
                # Upstash scan
                result = await self.client.scan(cursor, match=match, count=count)  # type: ignore
                # Upstash returns [cursor, [keys]]
                if isinstance(result, list) and len(result) == 2:
                    cursor_val = int(result[0]) if result[0] else 0
                    keys_val = result[1] if isinstance(result[1], list) else []
                    return cursor_val, keys_val
                return 0, []
            else:
                # Local Redis scan
                cursor_result, keys = await self.client.scan(cursor=cursor, match=match, count=count)  # type: ignore
                return int(cursor_result), list(keys) if keys else []
        except Exception as e:
            self._safe_warn(f"Failed to scan: {e}")
            return 0, []
    
    async def pipeline(self) -> RedisPipeline:
        """Create a pipeline for batch operations"""
        await self._ensure_client()
        
        if self._is_upstash:
            # Upstash doesn't support pipelines the same way
            # Return a mock pipeline that executes commands immediately
            return UpstashMockPipeline(self.client)  # type: ignore
        else:
            return self.client.pipeline()  # type: ignore
    
    # ============ GENERIC CACHE (USER-SCOPED) ============
    
    async def set_cache(self, user_id: str, key: str, value: Any, expire: Optional[int] = None) -> None:
        """Set a value in the cache"""
        full_key = f"user:{user_id}:cache:{key}"
        await self.set(full_key, json.dumps(value), ex=expire)
    
    async def get_cache(self, user_id: str, key: str) -> Optional[Any]:
        """Get a value from the cache"""
        full_key = f"user:{user_id}:cache:{key}"
        value = await self.get(full_key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    async def delete_cache(self, user_id: str, key: str) -> None:
        """Delete a value from the cache"""
        full_key = f"user:{user_id}:cache:{key}"
        await self.delete(full_key)
    
    async def clear_cache(self, user_id: str) -> None:
        """Clear all cache for a user"""
        pattern = f"user:{user_id}:cache:*"
        await self._delete_by_pattern(pattern)
    
    # ============ CONVERSATION HISTORY ============
    
    async def add_message(self, user_id: str, role: str, content: str) -> None:
        """Add a message to conversation history"""
        key = f"user:{user_id}:conversation"
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(NEPAL_TZ).isoformat()
        }
        await self.rpush(key, json.dumps(message))
        
        # Cache embedding in background
        asyncio.create_task(self._cache_embedding_with_user(content, user_id))
    
    async def _cache_embedding_with_user(self, text: str, user_id: str) -> None:
        """Background task to cache embedding"""
        try:
            from app.services.embedding_services import embedding_service
            embedding = await embedding_service.embed_single(text)
            await self._set_embedding_cache(user_id, text, embedding)
        except Exception as e:
            logger.debug(f"Failed to cache embedding: {e}")
    
    async def get_last_n_messages(self, user_id: str, n: int = 10) -> List[Dict[str, Any]]:
        """Get the last N messages from conversation history"""
        try:
            key = f"user:{user_id}:conversation"
            messages_raw = await self.lrange(key, -n, -1)
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
        except Exception as e:
            self._safe_warn(f"Failed to get messages for user '{user_id}': {e}")
            return []
    
    async def clear_conversation_history(self, user_id: str) -> None:
        """Clear all conversation history for a user"""
        key = f"user:{user_id}:conversation"
        await self.delete(key)
    
    # ============ EMBEDDING CACHE ============
    
    def _get_text_hash(self, text: str) -> str:
        """Generate hash for text"""
        return hashlib.md5(text.encode()).hexdigest()
    
    async def _get_embedding_cache(self, user_id: str, text: str) -> Optional[List[float]]:
        """Get cached embedding for text"""
        try:
            text_hash = self._get_text_hash(text)
            cache_key = f"user:{user_id}:emb:{text_hash}"
            cached = await self.get(cache_key)
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            logger.debug(f"Failed to get cached embedding: {e}")
            return None
    
    async def _batch_get_embedding_cache(
        self, 
        user_id: str, 
        texts: List[str]
    ) -> List[Optional[List[float]]]:
        """Batch cache retrieval using pipeline"""
        if not texts:
            return []
        
        try:
            cache_keys = [
                f"user:{user_id}:emb:{self._get_text_hash(text)}" 
                for text in texts
            ]
            
            pipeline = await self.pipeline()
            for key in cache_keys:
                pipeline.get(key)
            
            cached_values = await pipeline.execute()
            
            results: List[Optional[List[float]]] = []
            for cached in cached_values:
                if cached:
                    try:
                        results.append(json.loads(cached))
                    except:
                        results.append(None)
                else:
                    results.append(None)
            
            return results
        except Exception as e:
            logger.debug(f"Failed to batch get cached embeddings: {e}")
            return [None] * len(texts)
    
    async def _set_embedding_cache(self, user_id: str, text: str, embedding: List[float]) -> bool:
        """Cache an embedding"""
        try:
            text_hash = self._get_text_hash(text)
            cache_key = f"user:{user_id}:emb:{text_hash}"
            await self.set(cache_key, json.dumps(embedding), ex=EMBEDDING_TTL)
            return True
        except Exception as e:
            logger.debug(f"Failed to cache embedding: {e}")
            return False
    
    async def _batch_set_embedding_cache(
        self,
        user_id: str,
        texts: List[str],
        embeddings: List[List[float]]
    ) -> bool:
        """Batch cache setting using pipeline"""
        if not texts or not embeddings or len(texts) != len(embeddings):
            return False
        
        try:
            pipeline = await self.pipeline()
            
            for text, embedding in zip(texts, embeddings):
                text_hash = self._get_text_hash(text)
                cache_key = f"user:{user_id}:emb:{text_hash}"
                pipeline.setex(cache_key, EMBEDDING_TTL, json.dumps(embedding))
            
            await pipeline.execute()
            return True
        except Exception as e:
            logger.debug(f"Failed to batch cache embeddings: {e}")
            return False
    
    async def get_embeddings_for_messages(
        self,
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
        cached_embeddings = await self._batch_get_embedding_cache(user_id, texts)
        
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
            await self._batch_set_embedding_cache(user_id, texts_to_compute, new_embeddings)
        
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
        self,
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
        messages = await self.get_last_n_messages(user_id, n)
        if not messages:
            return []
        
        logger.info(f"🔍 Searching {len(messages)} messages for '{query[:50]}...'")
        
        # OPTIMIZATION: Parallel execution - get query + message embeddings simultaneously
        query_task = asyncio.create_task(
            self.get_embeddings_for_messages(user_id, [{"content": query}], "content")
        )
        messages_task = asyncio.create_task(
            self.get_embeddings_for_messages(user_id, messages, "content")
        )
        
        # Wait for both to complete
        query_embeddings, msg_embeddings = await asyncio.gather(query_task, messages_task)
        
        if not query_embeddings or not msg_embeddings:
            return []
        
        query_emb = np.array(query_embeddings[0])
        msg_embs = np.array(msg_embeddings)
        
        # OPTIMIZATION: Fast cosine similarity
        query_norm = query_emb / np.linalg.norm(query_emb)
        doc_norms = msg_embs / np.linalg.norm(msg_embs, axis=1, keepdims=True)
        similarities = doc_norms @ query_norm
        
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
    
    async def warm_embedding_cache(self, user_id: str, n: int = 500) -> int:
        """
        Pre-compute and cache embeddings for user's messages
        
        Args:
            user_id: User ID
            n: Number of messages to cache
            
        Returns:
            Number of embeddings cached
        """
        logger.info(f"🔥 Warming cache for user {user_id}: {n} messages")
        
        messages = await self.get_last_n_messages(user_id, n)
        if not messages:
            return 0
        
        await self.get_embeddings_for_messages(user_id, messages, "content")
        
        logger.info(f"✅ Cache warmed: {len(messages)} messages")
        return len(messages)
    
    # ============ USER DETAILS ============
    
    async def set_user_details(self, user_id: str, details: Dict[str, Any]) -> None:
        """Set user details"""
        key = f"user:{user_id}:details"
        await self.set(key, json.dumps(details))
    
    async def get_user_details(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user details"""
        key = f"user:{user_id}:details"
        details = await self.get(key)
        if details:
            try:
                return json.loads(details)
            except json.JSONDecodeError:
                return None
        return None
    
    async def clear_user_details(self, user_id: str) -> None:
        """Clear user details"""
        key = f"user:{user_id}:details"
        await self.delete(key)
    
    async def update_user_details(self, user_id: str, details: Dict[str, Any]) -> None:
        """Update user details (merge with existing)"""
        existing_details = await self.get_user_details(user_id)
        if existing_details is None:
            await self.set_user_details(user_id, details)
        else:
            existing_details.update(details)
            await self.set_user_details(user_id, existing_details)
    
    # ============ UTILITY METHODS ============
    
    async def _delete_by_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern"""
        cursor = 0
        total_deleted = 0
        
        while True:
            cursor, keys = await self.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await self.delete(*keys)
                total_deleted += len(keys)
            if cursor == 0:
                break
        
        return total_deleted
    
    async def clear_all_user_data(self, user_id: str) -> None:
        """Clear ALL data for a user"""
        pattern = f"user:{user_id}:*"
        total_deleted = await self._delete_by_pattern(pattern)
        
        if total_deleted > 0:
            logger.info(f"🗑️  Cleared all data for user {user_id}: {total_deleted} keys")
    
    async def clear_embedding_cache(self, user_id: str) -> int:
        """Clear all cached embeddings for a user"""
        pattern = f"user:{user_id}:emb:*"
        total_deleted = await self._delete_by_pattern(pattern)
        
        if total_deleted > 0:
            logger.info(f"🗑️  Cleared {total_deleted} cached embeddings")
        
        return total_deleted
    
    async def get_embedding_cache_stats(self, user_id: str) -> Dict[str, Any]:
        """Get cache statistics for a user"""
        try:
            pattern = f"user:{user_id}:emb:*"
            cursor = 0
            keys_list: List[str] = []
            
            while True:
                cursor, keys = await self.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    keys_list.extend(keys)
                if cursor == 0:
                    break
            
            # Sample for memory estimation
            total_size = 0
            if keys_list:
                sample_keys = keys_list[:min(10, len(keys_list))]
                for key in sample_keys:
                    val = await self.get(key)
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
    
    async def process_query_and_get_context(self, user_id: str, current_query: str) -> tuple[List[Dict[str, Any]], bool]:
        """
        OPTIMIZED: Check if Pinecone data is needed, with parallel operations
        
        This function checks whether pinecone data is needed or not. 
        If yes, pinecone data is returned; otherwise local data is used.
        """
        is_pinecone_needed = False
        
        # OPTIMIZATION: Run semantic search and message appending in parallel
        search_task = asyncio.create_task(
            self.semantic_search_messages(user_id, current_query)
        )
        append_task = asyncio.create_task(
            self._append_message_to_local_and_cloud(user_id, current_query)
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
    
    async def _append_message_to_local_and_cloud(self, user_id: str, current_query: str):
        """Append message to local Redis and cloud Pinecone"""
        from app.db.pinecone.config import upsert_query
        
        await self.add_message(user_id, "user", current_query)

        # Upsert to Pinecone in background
        asyncio.create_task(
            asyncio.to_thread(upsert_query, user_id, current_query)
        )


class UpstashMockPipeline:
    """Mock pipeline for Upstash (executes commands immediately)"""
    
    def __init__(self, client: Any):
        self.client = client
        self.commands: List[tuple] = []
    
    def get(self, key: str) -> 'UpstashMockPipeline':
        self.commands.append(('get', key))
        return self
    
    def setex(self, key: str, seconds: int, value: str) -> 'UpstashMockPipeline':
        self.commands.append(('setex', key, seconds, value))
        return self
    
    async def execute(self) -> List[Any]:
        """Execute all commands"""
        results = []
        for cmd in self.commands:
            if cmd[0] == 'get':
                result = await self.client.get(cmd[1])
                results.append(result)
            elif cmd[0] == 'setex':
                await self.client.setex(cmd[1], cmd[2], cmd[3])
                results.append(True)
        return results


# ============ SINGLETON INSTANCE ============

redis_manager = RedisManager()


# ============ CONVENIENCE FUNCTIONS (backward compatibility) ============

async def set_cache(user_id: str, key: str, value: Any, expire: Optional[int] = None) -> None:
    await redis_manager.set_cache(user_id, key, value, expire)

async def get_cache(user_id: str, key: str) -> Optional[Any]:
    return await redis_manager.get_cache(user_id, key)

async def delete_cache(user_id: str, key: str) -> None:
    await redis_manager.delete_cache(user_id, key)

async def clear_cache(user_id: str) -> None:
    await redis_manager.clear_cache(user_id)

async def add_message(user_id: str, role: str, content: str) -> None:
    await redis_manager.add_message(user_id, role, content)

async def get_last_n_messages(user_id: str, n: int = 10) -> List[Dict[str, Any]]:
    return await redis_manager.get_last_n_messages(user_id, n)

async def clear_conversation_history(user_id: str) -> None:
    await redis_manager.clear_conversation_history(user_id)

async def set_user_details(user_id: str, details: Dict[str, Any]) -> None:
    await redis_manager.set_user_details(user_id, details)

async def get_user_details(user_id: str) -> Optional[Dict[str, Any]]:
    return await redis_manager.get_user_details(user_id)

async def clear_user_details(user_id: str) -> None:
    await redis_manager.clear_user_details(user_id)

async def update_user_details(user_id: str, details: Dict[str, Any]) -> None:
    await redis_manager.update_user_details(user_id, details)

async def clear_all_user_data(user_id: str) -> None:
    await redis_manager.clear_all_user_data(user_id)

async def get_embeddings_for_messages(
    user_id: str,
    messages: List[Dict[str, str]],
    text_key: str = "content"
) -> List[List[float]]:
    return await redis_manager.get_embeddings_for_messages(user_id, messages, text_key)

async def semantic_search_messages(
    user_id: str,
    query: str,
    n: int = 500,
    top_k: int = 10,
    threshold: float = 0.5
) -> List[Dict[str, Any]]:
    return await redis_manager.semantic_search_messages(user_id, query, n, top_k, threshold)

async def warm_embedding_cache(user_id: str, n: int = 500) -> int:
    return await redis_manager.warm_embedding_cache(user_id, n)

async def clear_embedding_cache(user_id: str) -> int:
    return await redis_manager.clear_embedding_cache(user_id)

async def get_embedding_cache_stats(user_id: str) -> Dict[str, Any]:
    return await redis_manager.get_embedding_cache_stats(user_id)

async def process_query_and_get_context(user_id: str, current_query: str) -> tuple[List[Dict[str, Any]], bool]:
    return await redis_manager.process_query_and_get_context(user_id, current_query)