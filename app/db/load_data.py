from app.db.dbconfig import client

def load_data(collection_name):
    collection = client.get_or_create_collection(name=collection_name)
    collection.add(
        ids=["id1", "id2"],
        documents=[
            "This is a document about pineapple",
            "This is a document about oranges"
        ]
    )
    return collection
    