from app.cache.redis.config import set_cache, get_cache, delete_cache, clear_cache, add_message, get_last_n_messages, clear_conversation_history,compute_similarity,process_query_and_get_context,set_user_details,get_user_details,clear_user_details
import json

# from app.db.pinecone.config import (
#     get_user_all_queries,
#     search_user_queries
# )

# data = [{"data": 123, "name": "John", "age": 30}, {"data": 456, "name": "Jane", "age": 25}, {"data": 789, "name": "Doe", "age": 40},{"data": 101, "name": "Alice", "age": 28}]

# set_cache("test_key", data, expire=60)
# cached_value = get_cache("test_key") or []

# cached_value.append({"data": 112, "name": "Bob", "age": 35})
# cached_value.append({"data": 112, "name": "Bob", "age": 35})

# set_cache("test_key", cached_value, expire=60)


# clear_conversation_history("user_1")

# add_message("user_1", "user", "Hey i loved one girl very much, Her name was ankita.")
# add_message("user_1", "user", "I thought she would love me as i do . ")
# add_message("user_1", "assistant", "I'm fine, thank you!")
# add_message("user_1", "user", "I loved her so much , i could not stop thinking about her and i was so happy.")

# q = get_user_all_queries("user_1", top_k=20)
# print(f"\nAll queries for user_1 {json.dumps(q, indent=2)} found):")

# for t in q:
#   add_message("user_1", "user", t["query"])

# messages = get_last_n_messages("user_1")
# print("Last n Messages:", json.dumps(messages, indent=2))

# mess  = "I loved her so much ankita"
# res  = compute_similarity(mess, messages)
# print(f"\nSimilarity score: {res} for {mess} {json.dumps(messages, indent=2)} found):")




# context, state = process_query_and_get_context("user_1", "I loved her so much ankita", search_user_queries, get_user_all_queries, 0.3)

# context, state = process_query_and_get_context(
#   "user_1", 
#   "I loved her so much ankita", 
#   search_user_queries, 
#   get_user_all_queries,
#   0.3
#   )

# print(f"\nContext: {json.dumps(context, indent=2)} found):")

# print(f"\nState: {state} found):")

# set_user_details("user_1", {"name": "John Doe", "age": 30})

details = get_user_details("692e7408e468571218b2c47d")

print(f"\nDetails: {json.dumps(details, indent=2)} found):")

# clear_user_details("user_1")