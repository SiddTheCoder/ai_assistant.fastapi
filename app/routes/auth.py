from fastapi import APIRouter
from app.db.mongo import get_db
from app.models.chat_model import ChatModel
from app.utils.serialize_mongo_doc import serialize_id
from app.models.user_model import UserModel

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register-user")
async def register_user(user: UserModel):
  db = get_db()
  
  result = await db.users.insert_one(user.dict())
  return {"inserted_id": str(result.inserted_id)}

@router.post("/update-credentials")
async def get_data():
    db = get_db()
    res = await db.chats.find({"user_id": "12345"}).sort("created_at",-1).to_list(20)
    return serialize_id(res)


@router.get("/get-users")
async def get_users():
    db = get_db()
    res = await db.users.find({}).to_list()
    return serialize_id(res)