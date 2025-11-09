from app.db.pinecone.config import (
    upsert_query, 
    get_all_user_queries, 
    search_user_queries,
    get_index_stats
)
import time
import json

def test_upsert():
    """Test upserting queries"""
    print("\n=== Testing Upsert ===")
    upsert_query("user_1", "How to learn AI?")
    upsert_query("user_1", "Explain deep learning basics.")
    upsert_query("user_1", "What is vector database?")
    
    # Wait for indexing
    print("\n⏳ Waiting 5 seconds for Pinecone to index...")
    time.sleep(5)


def test_get_all():
    queries = get_all_user_queries("user_1")
    print(f"\nAll queries for user_1 {queries} found):")
    


def test_search():
    results = search_user_queries("user_1", "vector is part of math", top_k=5)
    print(f"\nSearch results for 'machine learning tutorials' {results} found):")
    # for i, result in enumerate(results, 1):
    #     print(f"  {i}. Query: {result['query']}")
    #     print(f"     Score: {result['score']:.4f}")
    #     print()


def test_stats():
    """Test index statistics"""
    print("\n=== Index Statistics ===")
    stats = get_index_stats()
    print(f"Total vectors: {stats.get('total_vector_count', 0)}")
    namespaces = stats.get('namespaces', {})
    for ns_name, ns_data in namespaces.items():
        print(f"Namespace '{ns_name}': {ns_data.get('vector_count', 0)} vectors")


if __name__ == "__main__":
    # Uncomment the test you want to run:
    
    # First time: Insert data
    # test_upsert()
    
    # # # # After data is inserted and indexed:
    # test_get_all()
    test_search()
    # test_stats()