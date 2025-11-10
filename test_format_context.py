from app.cache.redis.config import get_last_n_messages,compute_similarity,add_message,set_cache
from app.db.pinecone.config import search_user_queries,get_user_all_queries,upsert_query
import json
from app.utils.build_prompt import format_context,build_prompt


def test_format_context():
  recent_context = get_last_n_messages("user_1")
  query_based_context = get_user_all_queries("user_1")
  recent_str, query_str = format_context(recent_context, query_based_context)
  print(recent_str)
  print(query_str)

  prompt = build_prompt("neutral", "I loved one girl very much, Her name was ankita.", recent_context, query_based_context)
  print(prompt)

test_format_context()  
