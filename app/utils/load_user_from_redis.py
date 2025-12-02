from app.cache.redis.config import set_user_details,get_user_details,clear_user_details
from typing import Dict, Any
from bson import ObjectId
from app.utils.serialize_mongo_doc import serialize_doc

async def load_user(user_id: str) :
  details = get_user_details(user_id)
  if details is None or details == {} or details == "null":
    # call db and get user details
    from app.db.mongo import get_db
    db = get_db()
    print("Calling database to get user details for redis")
    details = await db.users.find_one({"_id":ObjectId(user_id)})
    if not details or details == {} or details == "null":
      return {}
    details = serialize_doc(details)
    set_user_details(user_id,details)
    return details
  print("already have user details in redis")
  return details  