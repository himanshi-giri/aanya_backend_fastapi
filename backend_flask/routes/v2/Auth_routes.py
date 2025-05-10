from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from database.db import new_users_collection
import jwt as pyjwt
from bson import ObjectId

router = APIRouter(prefix="/v2/auth", tags=["Auth"])

SECRET_KEY = "your_secret_key_here"  # Replace with a secure key
ALGORITHM = "HS256"


# === Pydantic Schemas ===

class SignupRequest(BaseModel):
    userId: str
    fullName: str
    email: EmailStr
    password: str
    role:str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# === Routes ===

@router.post('/signup')
async def register_user(request: SignupRequest):
    try:
        # Check if user already exists
        if new_users_collection.find_one({"email": request.email}):
            raise HTTPException(status_code=400, detail="User with this email already exists")

        # Create the user
        new_user = {
            "userId": request.userId,
            "fullName": request.fullName,
            "email": request.email,
            "password": request.password,
            "role":request.role,
            "createdAt": datetime.utcnow()
        }

        new_users_collection.insert_one(new_user)
        return {"message": "User created successfully", "userId": request.userId}

    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login_user(request: LoginRequest):
    try:
        user = new_users_collection.find_one({"email": request.email})
        if not user or user["password"] != request.password:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token_payload = {
            "userId": user["userId"],
            "email": user["email"],
            "exp": datetime.utcnow() + timedelta(days=1)
        }

        session_token = pyjwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)

        return {
            "message": "Login successful",
            "userId": user["userId"],
            "email": user["email"],
            "fullName": user["fullName"],
            "token": session_token
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print("Login error:", str(e))  # Add this line
        raise HTTPException(status_code=500, detail=str(e))
