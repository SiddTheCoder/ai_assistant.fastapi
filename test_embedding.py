import asyncio
import json
from app.cache.redis.config import get_last_n_messages
from app.utils.format_context import format_context
import datetime


query = "spark open notepad and write somethign about me"
 
async def main():
	documents = await get_last_n_messages("guest", n=500)
	print("Documents:", len(documents))
	# print(datetime.datetime.now())
	# similarity = await embedding_service.semantic_search(query, documents=documents, text_key="content" ,top_k=10)
	# print("Similarity all:", json.dumps(similarity, indent=2))
	# print(datetime.datetime.now())
	# recent_context, query_based_context = format_context([], similarity)
	# print("Query based context:", query_based_context)

    

asyncio.run(main())