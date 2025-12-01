from fastapi import APIRouter,Depends,Request
from app.db.mongo import get_db
from app.models.chat_model import ChatModel
from app.utils.serialize_mongo_doc import serialize_doc
from app.models.user_model import UserModel , UserResponse
from app.dependencies.auth import get_current_user
from app.jwt.config import create_access_token,create_refresh_token
from app.helper.email_validation import is_valid_email
from app.helper.response_helper import send_response, send_error
from bson import ObjectId
from datetime import datetime,timezone

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

@router.post("/register")
async def register_user(request: Request, user: UserModel):
    if not user.email or not is_valid_email(user.email):
        return send_error(
            message="Email address is required or Invalid email address",
            status_code=400
        )

    db = get_db()

    # 1️⃣ Check if user already exists
    existing_user = await db.users.find_one({"email": user.email})

    if existing_user and existing_user.get("is_user_verified", False):
        return send_error(
            message="User with this email already exists",
            status_code=409
        )
    
    try:
        user.username = user.email.split("@")[0]
        # 2️⃣ Insert user into MongoDB
        result = await db.users.insert_one(user.model_dump())
        if not result.inserted_id:
            return send_error(
                message="Failed to register user",
                status_code=500
            )

        user_id = str(result.inserted_id)

        # 3️⃣ Generate tokens
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)

        # 4️⃣ Update user document with refresh_token
        user_doc = await db.users.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": 
                {
                "refresh_token": refresh_token, 
                "last_login": datetime.now(timezone.utc)
                }
            },
            return_document=True  # return updated document
        )

        # 5️⃣ Serialize for JSON (ObjectId + datetime)
        user_doc = serialize_doc(user_doc)

        # 6️⃣ Send response with tokens
        return send_response(
            request=request,
            data=user_doc,
            access_token=access_token,
            refresh_token=refresh_token,
            message="User registered successfully",
            status_code=201
        )

    except Exception as e:
        return send_error(
            message="Failed to register user",
            status_code=500,
            errors=str(e)
        )

@router.post("/update-credentials")
async def get_data():
    db = get_db()
    res = await db.chats.find({"user_id": "12345"}).sort("created_at",-1).to_list(20)
    return serialize_doc(res)

@router.get("/me", response_model = UserResponse)
def get_me(user = Depends(get_current_user)):
    return serialize_doc(user)

@router.get("/get-users")
async def get_users():
    db = get_db()
    res = db.users.find({})
    return serialize_doc(res)