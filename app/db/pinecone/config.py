from pinecone import ( 
    Pinecone,
    IndexEmbed,
    CloudProvider,
    AwsRegion,
    Metric,
)
from app.config import settings
from typing import Optional, Dict, Any, List
import hashlib
import time
from datetime import datetime

pinecone_client = Pinecone(api_key=settings.pinecone_api_key)

# Check if the index exists
if not pinecone_client.has_index(settings.pinecone_index_name):
    print(f"No index named {settings.pinecone_index_name} found. Creating a new index...")
    pinecone_client.create_index_for_model(
        name=settings.pinecone_index_name,
        cloud=CloudProvider.AWS,
        region=AwsRegion.US_EAST_1,
        embed=IndexEmbed(
            model="llama-text-embed-v2",
            metric=Metric.COSINE,
            field_map={"text": "text"}
        )
    )
    print("⏳ Waiting for index to be ready...")
    time.sleep(10)
else:
    print(f"✅ Index already exists! named {settings.pinecone_index_name}")

pinecone_index = pinecone_client.Index(settings.pinecone_index_name)
pinecone_namespace = settings.pinecone_metadata_namespace


def generate_stable_id(user_id: str, query: str) -> str:
    """
    Generate a consistent ID using MD5 hash.
    Same input will ALWAYS produce the same ID.
    """
    content = f"{user_id}:{query}"
    return hashlib.md5(content.encode()).hexdigest()


def get_embedding(text: str) -> List[float]:
    """
    Get embedding for text using Pinecone's inference API.
    """
    try:
        # Use Pinecone's embed endpoint
        response = pinecone_client.inference.embed(
            model="llama-text-embed-v2",
            inputs=[text],
            parameters={"input_type": "passage"}
        )
        return response.data[0].values
    except Exception as e:
        print(f"❌ Embedding failed: {e}")
        raise


def upsert_query(user_id: str, query: str) -> None:
    """
    Upsert a user query into the Pinecone index.
    Uses stable ID so duplicate queries update instead of creating new records.
    """
    record_id = generate_stable_id(user_id, query)
    
    try:
        # Get embedding for the query
        embedding = get_embedding(query)
        
        # Upsert with metadata (traditional method)
        pinecone_index.upsert(
            vectors=[
                {
                    "id": record_id,
                    "values": embedding,
                    "metadata": {
                        "user_id": user_id,
                        "query": query,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            ],
            namespace=pinecone_namespace
        )
        print(f"✅ Upserted query for {user_id}: '{query[:50]}...' (ID: {record_id[:8]}...)")
    except Exception as e:
        print(f"[pinecone] Upsert failed: {e}")


def search_user_queries(user_id: str, search_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Search for similar queries for a specific user.
    """
    try:
        # Get embedding for search text
        embedding = get_embedding(search_text)
        
        # Search with filter
        results = pinecone_index.query(
            vector=embedding,
            top_k=top_k,
            namespace=pinecone_namespace,
            filter={"user_id": user_id},  # Simplified filter format
            include_metadata=True
        )
        
        # Type assertion to fix type checking
        """ getattr used to avoid type checking issues like 'QueryResults' has no attribute 'matches'  then  fall back to [] 
        """
        matches = getattr(results, 'matches', [])
        
        return [
            {
                "id": match.id,
                "score": match.score,
                "query": match.metadata.get("query", "") if match.metadata else "",
                "user_id": match.metadata.get("user_id", "") if match.metadata else "",
                "timestamp": match.metadata.get("timestamp", 0) if match.metadata else 0
                # Add more metadata as needed
            }
            for match in matches
        ]
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return []


def get_user_all_queries(user_id: str, top_k: int = 20) -> List[Dict[str, str]]:
    """
    Get all queries for a specific user.
    Uses a generic search term to retrieve all records.
    """
    try:
        # Get embedding for generic search
        embedding = get_embedding("all queries")
        
        # Query with filter
        results = pinecone_index.query(
            vector=embedding,
            top_k=top_k,
            namespace=pinecone_namespace,
            filter={"user_id": user_id},  # Simplified filter format
            include_metadata=True
        )
        
        # Type assertion to fix type checking
        matches = getattr(results, 'matches', [])

        extrcted_data = []
        
        for match in matches:
            if match.metadata:
                item = {
                    'query': match.metadata.get('query', ''),
                    'timestamp': match.metadata.get('timestamp', 0),
                    'user_id': match.metadata.get('user_id', ''),
                    'score': match.score if hasattr(match, 'score') else 0.0,
                    'id': match.id if hasattr(match, 'id') else ''
                }

                extrcted_data.append(item)

        return extrcted_data
    except Exception as e:
        print(f"❌ Failed to get queries: {e}")
        return []


def delete_user_query(user_id: str, query: str) -> bool:
    """
    Delete a specific query by generating its stable ID.
    """
    try:
        record_id = generate_stable_id(user_id, query)
        pinecone_index.delete(
            ids=[record_id],
            namespace=pinecone_namespace
        )
        print(f"🗑️ Deleted query for {user_id}: '{query[:50]}...'")
        return True
    except Exception as e:
        print(f"❌ Delete failed: {e}")
        return False


def delete_user_all_queries(user_id: str) -> bool:
    """
    Delete all queries for a specific user.
    """
    try:
        pinecone_index.delete(
            filter={"user_id": user_id},  # Simplified filter format
            namespace=pinecone_namespace
        )
        print(f"🗑️ Deleted all queries for {user_id}")
        return True
    except Exception as e:
        print(f"❌ Delete failed: {e}")
        return False


def get_index_stats() -> Dict[str, Any]:
    """
    Get statistics about the index.
    """
    try:
        stats = pinecone_index.describe_index_stats()
        return stats # type: ignore
    except Exception as e:
        print(f"❌ Failed to get stats: {e}")
        return {}