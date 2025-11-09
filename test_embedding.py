from app.db.pinecone.config import (
    get_embedding,
    generate_stable_id
)

a = generate_stable_id("user_1", "How todaqI?")
print(a)
print(f"Embedding length: {len(a)}")