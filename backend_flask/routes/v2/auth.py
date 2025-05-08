from fastapi import APIRouter,HTTPException;
from database.db import new_users_collection
from pydantic import BaseModel
from database.db import users_collection
from datetime import datetime, timedelta
import jwt
router = APIRouter(prefix="/v2",tags=["API"])

SECRET_KEY = "your_secret_key_here"

class LoginRequest(BaseModel):
    loginId: str
    password: str

@router.get('/users')
async def getusers():
    try:
        users_cursor = new_users_collection.find({})
        users = []
        for user in users_cursor:
            user['_id'] = str(user['_id'])  # Convert ObjectId to string
            users.append(user)
        return users
    except Exception as e:
        print("Error:", e)
        return {"error": "Failed to fetch users"}
    
@router.post("/login")
async def login(request: LoginRequest):
    try:
        user = users_collection.find_one({"loginId": request.loginId})
        if not user or request.password != user["password"]:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        print(jwt.__file__)
        print(dir(jwt))
        try:
            session_token = jwt.encode(
                {"loginId": request.loginId, "exp": datetime.utcnow() + timedelta(days=1)},
                SECRET_KEY,
                algorithm="HS256",
            )
        except Exception as jwt_error:
            print(jwt_error)
            raise HTTPException(status_code=300, detail=f"JWT encoding failed: {str(jwt_error)}")

        return {
            "message": "Login successful",
            "userId": str(user["_id"]),
            "role": user["role"],
            "sessionToken": session_token,
        }
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

