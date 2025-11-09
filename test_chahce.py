from app.cache.redis.config import set_cache, get_cache, delete_cache, clear_cache

# data = [{"data": 123, "name": "John", "age": 30}, {"data": 456, "name": "Jane", "age": 25}, {"data": 789, "name": "Doe", "age": 40},{"data": 101, "name": "Alice", "age": 28}]

# set_cache("test_key", data, expire=60)
# cached_value = get_cache("test_key") or []

# cached_value.append({"data": 112, "name": "Bob", "age": 35})

# set_cache("test_key", cached_value, expire=60)


cached_value = get_cache("test_key") or []
print("Cached Value:", cached_value)

user_queries = [item['name'] for item in cached_value]

print("User Queries:", user_queries)
for item in enumerate(cached_value or []):
    print(f"Index: {item[0]}, Item: {item[1]}")