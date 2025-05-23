# routes/v2/progress.py

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from database.db import progress_collection, challenges_collection, create_goal
from database.db import leaderboard_collection, login_collection
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
async def get_user_level_up_progress(user_id: str, user=Depends(get_current_user)):
    # Ensure the requested user_id matches the authenticated user
    if user_id != user["userId"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's progress")

    # Query leaderboard_collection for the user's document
    leaderboard_data = leaderboard_collection.find_one({"userId": user_id})

    # Initialize levelUpProgress array
    level_up_progress = []

    # If data exists, process improvements
    if leaderboard_data and "improvements" in leaderboard_data:
        # Sort improvements by date if timestamp exists, otherwise take as is
        sorted_improvements = sorted(
            leaderboard_data["improvements"],
            key=lambda x: x.get("timestamp", datetime.min),
            reverse=True  # Most recent first
        )
        
        # Take only the 3 most recent improvements
        for improvement in sorted_improvements[:3]:
            level_up_progress.append({
                "subject": improvement["subject"],
                "topic": improvement["topic"],
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
def get_completed_challenges_count(user=Depends(get_current_user)):
    user_id = user["userId"]
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    # Count challenges where the logged-in user is either creator or opponent
    count = challenges_collection.count_documents({
        "$or": [
            {"creator": user_id},
            {"opponent": user_id}
        ],
        "status": "started",
        "timestamp": { "$gte": one_week_ago }
    })

    return { "completedChallengesLastWeek": count }


@router.get("/questions/answered-last-week")
def get_questions_answered_count(user=Depends(get_current_user)):
    user_id = user["userId"]
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    # Query to find challenges where the user is creator or opponent
    challenges = list(challenges_collection.find({
        "$or": [
            {"creator": user_id},
            {"opponent": user_id}
        ],
        "status": "started",
        "timestamp": { "$gte": one_week_ago }
    }))
    print(f"Challenges found: {len(challenges)}")
    # Count total questions answered
    total_questions_answered = 0
    
    for challenge in challenges:
        # Check answers object for the logged-in user
        answers = challenge.get('answers', {})
        for user_key, user_answers in answers.items():
            # Check if the current user matches the logged-in user
            if user_key == user_id:
                # Count non-empty and non-null answers
                questions_answered = sum(1 for answer in user_answers 
                                         if answer and answer.strip() and answer != "null")
                total_questions_answered += questions_answered
    
    return { "questionsAnsweredLastWeek": total_questions_answered }







@router.post("/progress2/log-activity")
async def log_activity(user=Depends(get_current_user)):
    now = datetime.utcnow()
    today_date = now.date()

    # Check if login already logged today
    existing = login_collection.find_one({
        "userId": user["userId"],
        "loginDate": {
            "$gte": datetime(today_date.year, today_date.month, today_date.day),
            "$lt": datetime(today_date.year, today_date.month, today_date.day) + timedelta(days=1)
        }
    })

    if not existing:
        login_collection.insert_one({
            "userId": user["userId"],
            "loginDate": now,
            "timestamp": now
        })

    return {"message": "Activity logged"}




# @router.get("/loginStreak/daily-streak")
# def get_daily_streak(user=Depends(get_current_user)):
#     user_id = user["userId"]
#     try:
#         # Ensure user is authenticated
#         if not user_id:
#             raise HTTPException(status_code=403, detail="Not authorized to access this user's progress")
        
#         # user_id = user.get("userId")
        
#         # if not user_id:
#         #     raise HTTPException(status_code=403, detail="User ID not found")
        
#         # Get current date and week
#         current_date = datetime.now(timezone.utc).date()
#         start_of_week = current_date - timedelta(days=current_date.weekday())
#         end_of_week = start_of_week + timedelta(days=6)
#         print(user_id)
#         # Find login records for the current week
#         login_records = list(login_collection.find({
#             "userId": user_id,
#             "loginDate": {
#                 "$gte": start_of_week,
#                 "$lte": end_of_week
#             }
#         }))
        
#         # Calculate streak
#         consecutive_days = len(login_records)
#         login_dates = [record['loginDate'] for record in login_records]
        
#         return {
#             "dailyStreak": consecutive_days,
#             "loginDates": login_dates
#         }
    
#     except Exception as e:
#         print(f"Daily streak error: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))



@router.get("/progress2/stats")
async def get_user_progress(user=Depends(get_current_user)):
    IST_OFFSET = timedelta(hours=5, minutes=30)
    now = datetime.utcnow() + IST_OFFSET  # Convert UTC to IST

    # Start and end of the current week (Monday to Sunday)
    start_of_week = now - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # Get login dates in the current week
    logins = login_collection.find({
        "userId": user["userId"],
        "loginDate": {"$gte": start_of_week, "$lte": end_of_week}
    }).to_list(None)

    # Extract and convert login dates to local date
    login_days = sorted(set((login["loginDate"] + IST_OFFSET).date() for login in logins))

    # Calculate daily streak (ending today or yesterday)
    streak = 0
    today = now.date()
    for i in range(7):
        check_date = today - timedelta(days=i)
        if check_date in login_days:
            streak += 1
        else:
            break

    return {
        "dailyStreak": streak,
        "weeklyLoginDays": [d.isoformat() for d in login_days]
    }
    
    
    
    
@router.get("/progress2/pending-tasks")
async def get_pending_tasks(user=Depends(get_current_user)):
    user_id = user["userId"]
    current_date = datetime.now(timezone.utc)  # Make timezone-aware

    # Fetch pending tasks from create_goal collection
    pending_tasks = list(create_goal.find({
        "userId": user_id,
        "testDate": {"$lt": current_date.strftime("%Y-%m-%d")},  # Date in YYYY-MM-DD
        "status": "Not achieved",
        "progress": {"$lt": 50}
    }))

    processed_tasks = []
    for task in pending_tasks:
        # Calculate practices needed
        practices_needed = max(5 - (task['progress'] // 10), 1)

        # Calculate days since last practiced
        completed_at = task.get('completed_at')
        if completed_at:
            # Ensure completed_at is parsed as timezone-aware
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)
            days_ago = (current_date - completed_at).days
            last_practiced_str = f"{days_ago} days ago"
        else:
            last_practiced_str = "Not practiced yet"

        processed_tasks.append({
            "subject": task.get('subject', ''),
            "topic": task.get('topic', ''),
            "lastPracticed": last_practiced_str,
            "progress": task.get('progress', 0),
            "practicesNeeded": f"Practice {practices_needed} more times to get mastery"
        })

    return processed_tasks
