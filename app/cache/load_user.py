"""
Multi-Layer User Cache: Memory → Redis → MongoDB
Reduces user lookup from ~50ms to <1ms for cached users

IMPORTANT: Memory cache is process-local. For multi-worker deployments,
Redis remains the source of truth between processes.

Performance Tiers:
- Memory cache: <1ms (Python dict, per-process)
- Redis cache: ~5-10ms (shared across processes)
- MongoDB: ~30-50ms (database query)
"""
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from bson import ObjectId

from app.cache.redis.config import set_user_details, get_user_details, clear_user_details
from app.utils.serialize_mongo_doc import serialize_doc

logger = logging.getLogger(__name__)


class UserCache:
    """
    Three-tier caching strategy for user data.
    
    Layer 1: In-memory dict (fastest, <1ms, per-process)
    Layer 2: Redis (fast, ~5-10ms, shared across processes)
    Layer 3: MongoDB (slowest, ~30-50ms)
    
    NOTE: Memory cache is NOT shared between processes/workers!
    Each Gunicorn/Uvicorn worker has its own memory cache.
    """
    
    # In-memory cache: {user_id: (user_details, cached_at)}
    _memory_cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
    
    # Cache TTL settings
    MEMORY_TTL_SECONDS = 60  # 1 minute for memory cache
    REDIS_TTL_SECONDS = 300  # 5 minutes for Redis cache
    
    @classmethod
    def get_user(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user from cache (sync version for backwards compatibility).
        
        Args:
            user_id: MongoDB ObjectId as string
        
        Returns:
            User details dict or None if not found
        """
        now = datetime.utcnow()
        
        # ===== LAYER 1: Check Memory Cache =====
        if user_id in cls._memory_cache:
            details, cached_at = cls._memory_cache[user_id]
            
            # Check if still fresh
            if now - cached_at < timedelta(seconds=cls.MEMORY_TTL_SECONDS):
                logger.debug(f"⚡ Memory cache HIT for user {user_id}")
                return details
            else:
                # Expired, remove from cache
                del cls._memory_cache[user_id]
                logger.debug(f"♻️ Memory cache EXPIRED for user {user_id}")
        
        # ===== LAYER 2: Check Redis Cache =====
        logger.debug(f"🔍 Memory cache MISS, checking Redis for user {user_id}")
        details = get_user_details(user_id)
        
        if details and details != {} and details != "null":
            # Found in Redis, store in memory for next time
            cls._memory_cache[user_id] = (details, now)
            logger.debug(f"📦 Redis cache HIT for user {user_id}, stored in memory")
            return details
        
        # Cache MISS - will need database query
        logger.debug(f"❌ Redis cache MISS for user {user_id}")
        return None
    
    @classmethod
    async def load_user(cls, user_id: str) -> Dict[str, Any]:
        """
        Load user with three-tier caching strategy.
        
        Performance:
        - Memory hit: <1ms
        - Redis hit: ~5-10ms
        - Database hit: ~30-50ms (then cached for future)
        
        Args:
            user_id: MongoDB ObjectId as string
        
        Returns:
            User details dict (empty dict if user not found)
        """
        
        # Validate user_id is not empty
        if not user_id or user_id == "null" or user_id == "undefined":
            logger.warning(f"⚠️ Invalid user_id provided: {user_id}")
            return {}
        
        # Try cache layers first
        cached_user = cls.get_user(user_id)
        if cached_user is not None:
            return cached_user
        
        # ===== LAYER 3: Query MongoDB =====
        logger.info(f"💾 Database query for user {user_id}")
        
        try:
            from app.db.mongo import get_db
            db = get_db()
            
            details = await db.users.find_one({"_id": ObjectId(user_id)})
            
            if not details or details == {} or details == "null":
                logger.warning(f"⚠️ User {user_id} not found in database")
                return {}
            
            # Serialize MongoDB document
            details = serialize_doc(details)
            
            # CRITICAL: Store in both Redis and memory with the SAME key
            now = datetime.utcnow()
            set_user_details(user_id, details)  # Redis
            cls._memory_cache[user_id] = (details, now)  # Memory
            
            logger.info(f"✅ User {user_id} loaded from database and cached (memory + Redis)")
            return details
            
        except Exception as e:
            logger.error(f"❌ Failed to load user {user_id}: {e}", exc_info=True)
            return {}
    
    @classmethod
    def invalidate_user(cls, user_id: str):
        """
        Invalidate user cache across all layers.
        
        Call this when:
        - User updates profile/settings
        - API keys changed
        - Quota status manually reset
        
        NOTE: Only clears memory cache in THIS process.
        For multi-worker setups, Redis is cleared (shared state).
        """
        # Remove from memory (this process only)
        if user_id in cls._memory_cache:
            del cls._memory_cache[user_id]
            logger.debug(f"🗑️ Memory cache invalidated for user {user_id} (this process)")
        
        # Remove from Redis (affects all processes)
        clear_user_details(user_id)
        logger.info(f"🧹 Redis cache cleared for user {user_id} (affects all workers)")
    
    @classmethod
    def update_user_field(cls, user_id: str, field: str, value: Any):
        """
        Update a specific field in cached user data WITHOUT full reload.
        
        Use for hot-path updates like quota flags without full invalidation.
        
        IMPORTANT: Updates both memory (this process) and Redis (all processes).
        
        Args:
            user_id: User ID
            field: Field name (e.g., 'is_gemini_api_quota_reached')
            value: New value
        """
        # Update memory cache if exists (this process only)
        if user_id in cls._memory_cache:
            details, cached_at = cls._memory_cache[user_id]
            details[field] = value
            cls._memory_cache[user_id] = (details, cached_at)
            logger.debug(f"✏️ Updated {field}={value} in memory cache for user {user_id}")
        
        # Update Redis (affects all processes)
        redis_details = get_user_details(user_id)
        if redis_details and redis_details != {} and redis_details != "null":
            redis_details[field] = value
            set_user_details(user_id, redis_details)
            logger.debug(f"✏️ Updated {field}={value} in Redis for user {user_id}")
        else:
            logger.warning(f"⚠️ Cannot update field {field} - user {user_id} not in Redis")
    
    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        """Get cache statistics for monitoring/debugging (this process only)."""
        return {
            "memory_cached_users": len(cls._memory_cache),
            "memory_ttl_seconds": cls.MEMORY_TTL_SECONDS,
            "redis_ttl_seconds": cls.REDIS_TTL_SECONDS,
            "cached_user_ids": list(cls._memory_cache.keys()),
            "process_note": "Memory cache is per-process, not shared across workers"
        }
    
    @classmethod
    def clear_all_memory(cls):
        """Clear all in-memory caches in THIS process (Redis remains intact)."""
        count = len(cls._memory_cache)
        cls._memory_cache.clear()
        logger.warning(f"🧹 Cleared {count} users from memory cache (this process only)")


# ============================================================================
# CONVENIENCE FUNCTIONS (backwards compatible with your existing code)
# ============================================================================

async def load_user(user_id: str) -> Dict[str, Any]:
    """
    Load user with automatic multi-layer caching.
    
    Drop-in replacement for your existing load_user function.
    
    Performance improvement:
    - Before: Always 30-50ms (Redis or MongoDB)
    - After: <1ms for memory hits, ~5ms for Redis hits
    
    Usage:
        ```python
        user_details = await load_user(user_id)
        ```
    
    NOTE: Memory cache is per-process. In multi-worker setups:
    - Worker 1 may have user in memory
    - Worker 2 may need to fetch from Redis
    - This is NORMAL and expected behavior
    """
    return await UserCache.load_user(user_id)


def invalidate_user_cache(user_id: str):
    """
    Invalidate user cache when data changes.
    
    Clears:
    - Memory cache (this process)
    - Redis cache (all processes)
    
    Usage:
        ```python
        @app.post("/settings/update")
        async def update_settings(user_id: str = Depends(get_current_user)):
            # Update database
            await db.users.update_one(...)
            
            # Invalidate cache so next request gets fresh data
            invalidate_user_cache(user_id)
        ```
    """
    UserCache.invalidate_user(user_id)


def update_user_quota_flag(user_id: str, provider: str, quota_reached: bool):
    """
    Hot-update quota flags without full cache invalidation.
    
    More efficient than full invalidation for high-frequency updates.
    Updates both memory (this process) and Redis (all processes).
    
    Usage:
        ```python
        # Update Gemini quota flag
        update_user_quota_flag(user_id, "gemini", quota_reached=True)
        ```
    """
    field = f"is_{provider}_api_quota_reached"
    UserCache.update_user_field(user_id, field, quota_reached)


# ============================================================================
# FASTAPI DEPENDENCY EXAMPLE
# ============================================================================

async def get_current_user_cached(user_id: str) -> Dict[str, Any]:
    """
    FastAPI dependency for getting user with caching.
    
    Usage:
        ```python
        @app.post("/chat")
        async def chat(
            request: ChatRequest,
            user: Dict = Depends(get_current_user_cached)
        ):
            # user is already cached!
            return {"message": "Hello " + user.get("name")}
        ```
    """
    return await load_user(user_id)


# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

def log_cache_performance():
    """
    Log cache statistics for monitoring (this process only).
    
    Returns:
        Dict with cache stats including:
        - memory_cached_users: Number of users in THIS process's memory
        - cached_user_ids: List of user IDs cached in THIS process
    """
    stats = UserCache.get_cache_stats()
    logger.info(
        f"📊 User Cache Stats (Process {id(UserCache)}): "
        f"{stats['memory_cached_users']} users in memory"
    )
    return stats


# ============================================================================
# TEST UTILITY (for debugging cache behavior)
# ============================================================================

def debug_cache_state(user_id: str):
    """
    Debug helper to check cache state for a specific user.
    
    Returns:
        Dict showing where user data exists:
        - in_memory: bool
        - in_redis: bool
        - redis_data: Dict or None
    """
    in_memory = user_id in UserCache._memory_cache
    redis_data = get_user_details(user_id)
    in_redis = redis_data is not None and redis_data != {} and redis_data != "null"
    
    return {
        "user_id": user_id,
        "in_memory": in_memory,
        "in_redis": in_redis,
        "redis_data_preview": {
            k: v for k, v in (redis_data or {}).items() 
            if k in ['_id', 'username', 'email', 'is_gemini_api_quota_reached']
        } if in_redis else None,
        "process_id": id(UserCache),
        "note": "Memory cache is per-process - separate test.py runs won't share cache"
    }