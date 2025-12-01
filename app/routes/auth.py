from fastapi import APIRouter,Depends,Request
from app.db.mongo import get_db
from app.utils.serialize_mongo_doc import serialize_doc
from app.models.user_model import UserModel , UserResponse
from app.schemas import auth_schema
from app.dependencies.auth import get_current_user
from app.jwt.config import create_access_token,create_refresh_token
from app.helper.email_validation import is_valid_email
from app.helper.response_helper import send_response, send_error
from bson import ObjectId
from datetime import datetime,timezone,timedelta
from app.utils.generate_random_number import generate_otp
from app.emails import verification_email
from pymongo import ReturnDocument

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

    if existing_user and existing_user["is_user_verified"] == True:
        return send_error(
            message="User with this email already exists",
            status_code=409
        )
    
    if existing_user and existing_user["is_user_verified"] == False:
        new_otp = generate_otp(6)
        updated_user = await db.users.find_one_and_update(
            {"_id": existing_user["_id"]},
             {"$set": 
                {
                "last_login": datetime.now(timezone.utc),
                "verification_token": new_otp,
                "verification_token_expires": datetime.now(timezone.utc) + timedelta(minutes=10)
                }
            },
            return_document=ReturnDocument.AFTER
        )

        # Serialize for JSON (ObjectId + datetime)
        user_doc = serialize_doc(updated_user)

        # Send verification email
        verification_email.send(
        to_email=user.email,
        user_name=updated_user["username"],
        otp_code=new_otp,
        )

        # Send response with tokens
        return send_response(
            request=request,
            data={
                "user": user_doc,
                "emailStatus" : "Verification Token Sent"
            },
            message="User registered successfully",
            status_code=201
        )


    # create new user if no existing user
    try:
        user.username = user.email.split("@")[0]
        result = await db.users.insert_one(user.model_dump())
        if not result.inserted_id:
            return send_error(
                message="Failed to register user",
                status_code=500
            )

        user_id = str(result.inserted_id)

        # generate otp code for verification
        otp_code = generate_otp(6)

        # Update user document with refresh_token
        user_doc = await db.users.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": 
                {
                "last_login": datetime.now(timezone.utc),
                "verification_token": otp_code,
                "verification_token_expires": datetime.now(timezone.utc) + timedelta(minutes=10)
                }
            },
            return_document=ReturnDocument.AFTER
        )

        # Serialize for JSON (ObjectId + datetime)
        user_doc = serialize_doc(user_doc)

        # Send verification email
        verification_email.send(
        to_email=user.email,
        user_name=user.username,
        otp_code=otp_code,
        )

        # Send response with tokens
        return send_response(
            request=request,
            data={
                "user": user_doc,
                "emailStatus" : "Verification Token Sent"
            },
            message="User registered successfully",
            status_code=201
        )

    except Exception as e:
        return send_error(
            message="Failed to register user",
            status_code=500,
            errors=str(e)
        )

@router.post("/verify-otp")
async def verify_otp_code(request: Request, data : auth_schema.VerifyTokenData):

    if not data.email or not is_valid_email(data.email):
        return send_error(
            message="Email address is required or Invalid email address",
            status_code=400
        )
    
    if not data.otp or len(data.otp) != 6:
        return send_error(
            message="OTP is required and should be 6 digits",
            status_code=400
        )

    # get db connection
    db = get_db()
    user = await db.users.find_one({"email": data.email})

    if not user:
        return send_error(
            message="User not found",
            status_code=404
        )

    if not user["verification_token"] or not user["verification_token_expires"]:
        return send_error(
            message="Verification token not found",
            status_code=400
        )

    if user["verification_token"] != data.otp:
        return send_error(
            message="Invalid verification token",
            status_code=400
        )
    
    current_time = datetime.now(timezone.utc)
    expires_time = user["verification_token_expires"]
    if expires_time.tzinfo is None:
        expires_time = expires_time.replace(tzinfo=timezone.utc)

    if expires_time < current_time:
        return send_error(
            message="Verification token has expired",
            status_code=400
        )

    user_id = str(user["_id"])
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    user_doc = await db.users.find_one_and_update(
        {"_id": ObjectId(user["_id"])},
        {"$set": 
                { 
                "refresh_token": refresh_token,
                "last_login": datetime.now(timezone.utc),
                "verification_token_expires": None,
                "is_user_verified": True
                }
            },
            return_document=ReturnDocument.AFTER 
    )

    user_doc = serialize_doc(user_doc)

    return send_response(
        request=request,
        data={
            "user": user_doc,
            "emailStatus" : "Verified"
        },
        access_token=access_token,
        refresh_token=refresh_token,
        message="User verified successfully",
        status_code=200
    )

@router.get("/me", response_model = UserResponse)
def get_me(user = Depends(get_current_user)):
    return serialize_doc(user)

@router.get("/get-users")
async def get_users():
    db = get_db()
    res = db.users.find({})
    return serialize_doc(res)