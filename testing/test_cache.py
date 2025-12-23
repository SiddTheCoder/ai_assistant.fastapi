from app.cache.load_user import load_user,get_current_user_cached,log_cache_performance

import asyncio
user = asyncio.run(load_user("guest"))
print("User Data:", user)

a = log_cache_performance()
print("Cache Performance Logged", a)