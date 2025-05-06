from flask.cli import load_dotenv
from fastapi import APIRouter, HTTPException ,Request
from database.db import users_collection,role_menu_collection
import jwt
from datetime import datetime
import os
import dotenv

load_dotenv()

router = APIRouter(prefix="/users", tags=["Users"])

SECRET_KEY = os.getenv("SECRET_KEY")


@router.get("/data")
async def get_data():
    try:
        if users_collection is None:
            raise HTTPException(status_code=500, detail="Database not initialized.")

        data = list(users_collection.find({}, {"_id": 0}))
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/role")
async def role_data():
    try:
        data = list(role_menu_collection.find({}, {"_id": 0}))
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-options")
async def get_options(request: Request):
    try:
        user_id = request.headers.get("User-Id")
        user_role = request.headers.get("Role")
        session_token = request.headers.get("Session-Token")

        if not user_id or not user_role or not session_token:
            raise HTTPException(status_code=400, detail="Missing authentication headers")

        # Verify the session token
        try:
            decoded_token = jwt.decode(session_token, SECRET_KEY, algorithms=["HS256"])
            token_expiry = decoded_token.get("exp")
            if datetime.now().timestamp() > token_expiry:
                raise HTTPException(status_code=401, detail="Session token has expired")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Session token expired")
        except jwt.DecodeError:
            raise HTTPException(status_code=401, detail="Invalid session token")

        # Query MongoDB for options
        options_data = role_menu_collection.find_one({"role": user_role}, {"_id": 0})
        if not options_data:
            raise HTTPException(status_code=404, detail="No options found for this role")

        return options_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

