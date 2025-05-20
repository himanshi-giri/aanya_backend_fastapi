# routes/v2/progress.py

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from database.db import progress_collection, challenges_collection
from database.db import leaderboard_collection
#from models.models import UserProgress
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import List, Optional
import jwt as pyjwt
import os
from dotenv import load_dotenv
load_dotenv()
# from datetime import datetime


# from flask import Blueprint, request, jsonify
# from datetime import datetime, timedelta
# from config.db import db

# progress = Blueprint('progress', _name_)

router = APIRouter(prefix="/progress", tags=["Progress"])

SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_here")
ALGORITHM = "HS256"

# Pydantic model for each level-up improvement
class LevelUpImprovement(BaseModel):
    subject: str
    topic: str
    progress: int
    previousLevel: str
    newLevel: str

# Pydantic model for the response
class LevelUpProgressResponse(BaseModel):
    levelUpProgress: List[LevelUpImprovement]

class TopicProgress(BaseModel):
    topic_name: str
    subject: str
    last_practiced: datetime
    level: str
    practice_needed_for_mastery: int
    practice_done: int

class CompletedTask(BaseModel):
    message: str
    date: datetime

class WeeklyStats(BaseModel):
    challenges_completed: int
    questions_answered: int
    daily_streak: int
    study_time_minutes: int  # store as minutes, convert on frontend

class UserProgress(BaseModel):
    email: str
    levels: dict  # e.g., {"Quadratic Equation": "Proficient"}
    completed_tasks: List[CompletedTask]
    pending_tasks: List[TopicProgress]
    weekly_stats: WeeklyStats

# Decode token function 
def decode_token(request: Request) -> Optional[dict]:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except pyjwt.ExpiredSignatureError:
            return None
        except pyjwt.InvalidTokenError:
            return None
    return None

# Get current user function 
def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = auth_header.split(" ")[1]
    try:
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# GET endpoint to fetch user-specific level-up improvements
@router.get("/{user_id}", response_model=LevelUpProgressResponse)
async def get_user_level_up_progress(user_id: str,user=Depends(get_current_user)):
    # Ensure the requested user_id matches the authenticated user
    if user_id != user["userId"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's progress")

    # Query leaderboard_collection for the user's document
    leaderboard_data = leaderboard_collection.find_one({"userId": user_id})

    # Initialize levelUpProgress array
    level_up_progress = []

    # If data exists, process improvements
    if leaderboard_data and "improvements" in leaderboard_data:
        for improvement in leaderboard_data["improvements"]:
            level_up_progress.append({
                "subject": improvement["subject"],
                "topic" : improvement["topic"],
                "progress": 100,  # Completed level-up
                "previousLevel": improvement["previous_level"],
                "newLevel": improvement["new_level"]
            })

    # Return response
    return {"levelUpProgress": level_up_progress}

# @router.get("/{user_id}", response_model=LevelUpProgressResponse)
# async def get_user_level_up_progress(user_id: str, user=Depends(get_current_user)):
#     return {"message": f"Received request for user_id: {user_id}"}

@router.post("/update")
async def update_progress(progress: UserProgress):
    result = progress_collection.update_one(
        {"email": progress.email},
        {"$set": progress.dict()},
        upsert=True
    )
    return {"message": "Progress updated successfully"}

# @router.get("/{email}")
# async def get_user_progress(email: str):
#     user = progress_collection.find_one({"user_id": email})
#     if not user:
#         raise HTTPException(status_code=404, detail="User progress not found")
#     user["_id"] = str(user["_id"])
#     print(user)
#     return user


@router.get("/challenges/completed-last-week")
def get_completed_challenges_count(opponentId: str = Query(...)):
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    count = challenges_collection.count_documents({
        "opponent": opponentId,
        "status": "completed",
        "createdAt": { "$gte": one_week_ago }
    })

    return { "completedChallengesLastWeek": count }