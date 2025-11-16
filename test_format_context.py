from app.cache.redis.config import get_last_n_messages,compute_similarity,add_message,set_cache
from app.db.pinecone.config import search_user_queries,get_user_all_queries,upsert_query
import json
from app.utils.build_prompt import format_context,build_prompt


def test_format_context():
  text = "When did i slept yesterday ?"
  recent_context = get_last_n_messages("user_1", n=3)
  print("Recent context:", json.dumps(recent_context, indent=2))
  query_based_context = search_user_queries("user_1", text ,top_k=3)
  print("Query based context:", json.dumps(query_based_context, indent=2))

  recent_str, query_str = format_context(recent_context, query_based_context)

  print("Recent str:",recent_str)
  print("Query str:",query_str)

  # prompt = build_prompt("neutral", "I loved one girl very much, Her name was ankita.", recent_context, query_based_context)
  # print(prompt)

test_format_context()  
