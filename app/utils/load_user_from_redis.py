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
    
    Layer 1: In-memory dict (fastest, <1ms)
    Layer 2: Redis (fast, ~5-10ms)
    Layer 3: MongoDB (slowest, ~30-50ms)
    """
    
    # In-memory cache: {user_id: (user_details, cached_at)}
    _memory_cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
    
    # Cache TTL settings
    MEMORY_TTL_SECONDS = 60  # 1 minute for memory cache
    REDIS_TTL_SECONDS = 300  # 5 minutes for Redis cache
    
    @classmethod
    async def get_user(cls, user_id: str) -> Optional[Dict[str, Any]]:
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
        details = await get_user_details(user_id)
        
        if details and details != {} and details != "null":
            # Found in Redis, store in memory for next time
            cls._memory_cache[user_id] = (details, now)
            logger.debug(f"📦 Redis cache HIT for user {user_id}")
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
        
        # Try cache layers first
        cached_user = await cls.get_user(user_id)
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
            
            # Store in both Redis and memory
            now = datetime.utcnow()
            await set_user_details(user_id, details)
            cls._memory_cache[user_id] = (details, now)
            
            logger.info(f"✅ User {user_id} loaded from database and cached")
            return details
            
        except Exception as e:
            logger.error(f"❌ Failed to load user {user_id}: {e}", exc_info=True)
            return {}
    
    @classmethod
    async def invalidate_user(cls, user_id: str):
        """
        Invalidate user cache across all layers.
        
        Call this when:
        - User updates profile/settings
        - API keys changed
        - Quota status manually reset
        """
        # Remove from memory
        if user_id in cls._memory_cache:
            del cls._memory_cache[user_id]
            logger.debug(f"🗑️ Memory cache invalidated for user {user_id}")
        
        # Remove from Redis
        await clear_user_details(user_id)
        logger.info(f"🧹 All caches cleared for user {user_id}")
    
    @classmethod
    async def update_user_field(cls, user_id: str, field: str, value: Any):
        """
        Update a specific field in cached user data.
        
        Use for hot-path updates like quota flags without full invalidation.
        
        Args:
            user_id: User ID
            field: Field name (e.g., 'is_gemini_api_quota_reached')
            value: New value
        """
        # Update memory cache if exists
        if user_id in cls._memory_cache:
            details, cached_at = cls._memory_cache[user_id]
            details[field] = value
            cls._memory_cache[user_id] = (details, cached_at)
            logger.debug(f"✏️ Updated {field} in memory cache for user {user_id}")
        
        # Update Redis
        redis_details = await get_user_details(user_id)
        if redis_details and redis_details != {} and redis_details != "null":
            redis_details[field] = value
            await set_user_details(user_id, redis_details)
            logger.debug(f"✏️ Updated {field} in Redis for user {user_id}")
    
    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        """Get cache statistics for monitoring/debugging."""
        return {
            "memory_cached_users": len(cls._memory_cache),
            "memory_ttl_seconds": cls.MEMORY_TTL_SECONDS,
            "redis_ttl_seconds": cls.REDIS_TTL_SECONDS,
            "cached_user_ids": list(cls._memory_cache.keys())
        }
    
    @classmethod
    def clear_all_caches(cls):
        """Clear all in-memory caches (Redis remains intact)."""
        cls._memory_cache.clear()
        logger.warning("🧹 All memory caches cleared")


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
    """
    return await UserCache.load_user(user_id)


async def invalidate_user_cache(user_id: str):
    """
    Invalidate user cache when data changes.
    
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
    await UserCache.invalidate_user(user_id)


async def update_user_quota_flag(user_id: str, provider: str, quota_reached: bool):
    """
    Hot-update quota flags without full cache invalidation.
    
    More efficient than full invalidation for high-frequency updates.
    
    Usage:
        ```python
        # Update Gemini quota flag
        update_user_quota_flag(user_id, "gemini", quota_reached=True)
        ```
    """
    field = f"is_{provider}_api_quota_reached"
    await UserCache.update_user_field(user_id, field, quota_reached)


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
    """Log cache statistics for monitoring."""
    stats = UserCache.get_cache_stats()
    logger.info(f"📊 User Cache Stats: {stats['memory_cached_users']} users in memory")
    return stats