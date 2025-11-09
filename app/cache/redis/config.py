import redis
import json
from typing import Any, Optional, cast, Union

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
