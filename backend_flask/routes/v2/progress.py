# routes/v2/progress.py

from fastapi import APIRouter, HTTPException, Query
from database.db import progress_collection, challenges_collection
from models.models import UserProgress
from datetime import datetime, timedelta, timezone
from bson import ObjectId
# from datetime import datetime


# from flask import Blueprint, request, jsonify
# from datetime import datetime, timedelta
# from config.db import db

# progress = Blueprint('progress', __name__)

router = APIRouter(prefix="/progress", tags=["Progress"])

@router.post("/update")
async def update_progress(progress: UserProgress):
    result = progress_collection.update_one(
        {"email": progress.email},
        {"$set": progress.dict()},
        upsert=True
    )
    return {"message": "Progress updated successfully"}

@router.get("/{email}")
async def get_user_progress(email: str):
    user = progress_collection.find_one({"user_id": email})
    if not user:
        raise HTTPException(status_code=404, detail="User progress not found")
    user["_id"] = str(user["_id"])
    return user


@router.get("/challenges/completed-last-week")
def get_completed_challenges_count(opponentId: str = Query(...)):
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    count = challenges_collection.count_documents({
        "opponent": opponentId,
        "status": "completed",
        "createdAt": { "$gte": one_week_ago }
    })

    return { "completedChallengesLastWeek": count }