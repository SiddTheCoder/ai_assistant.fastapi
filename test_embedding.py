from app.services.embedding_services import get_embedding,embedding_service
import asyncio
import json
from app.cache.redis.config import get_last_n_messages
from app.utils.format_context import format_context


query = "spark open notepad and write somethign about me"
 
async def main():
	documents = get_last_n_messages("guest", n=10)
	print("Documents:", json.dumps(documents, indent=2))
	similarity = await embedding_service.semantic_search(query, documents=documents, text_key="content" ,top_k=5)
	print("Similarity:", json.dumps(similarity, indent=2))
	
	recent_context, query_based_context = format_context([], similarity)
	print("Query based context:", query_based_context)

    

asyncio.run(main())