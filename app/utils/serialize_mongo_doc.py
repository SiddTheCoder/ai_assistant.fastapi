def serialize_id(doc):
    """
    Convert Mongo ObjectId to string for JSON.
    Can also accept list of docs.
    """
    if isinstance(doc, list):
        return [serialize_id(d) for d in doc]

    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc