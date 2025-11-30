from fastapi import APIRouter
from app.db.mongo import get_db
from app.models.chat_model import ChatModel
from app.utils.serialize_mongo_doc import serialize_id

router = APIRouter(prefix="/crud", tags=["Chat"])

# @router.post("/save")
# async def save_chat(chat: ChatModel):
#     db = get_db()
#     result = await db.chats.insert_one(chat.dict())
#     return {"inserted_id": str(result.inserted_id)}

# TODO :
"""If you forget to serialize _id in any collection, the same error occurs:
memory
socket_logs
users
So usually I wrap all Mongo returns in serialize_id().
"""

@router.get("/")
async def get_data():
    db = get_db()
    res = await db.chats.find({"user_id": "12345"}).sort("created_at",-1).to_list(20)
    return serialize_id(res)