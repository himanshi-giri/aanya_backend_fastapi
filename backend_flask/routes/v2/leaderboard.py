from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from typing import  List, Dict, Optional
from datetime import datetime
from bson import ObjectId
from database.db import  leaderboard_collection, new_users_collection

router = APIRouter(prefix="/v2", tags=["Leaderboard_v1"])


#route for getting leaderboard info from leaderboard collection and user collection
 
# @router.get("/leaderboard")
# async def get_leaderboard():
#     leaderboard_data = []
#     leaderboard_entries = leaderboard_collection.find().sort("score", -1)

#     for entry in leaderboard_entries:
#         user = new_users_collection.find_one({"_id": entry["user_id"]})
#         if user:
#             leaderboard_data.append({
#                 "name": user.get("fullName", "N/A"),
#                 "school": user.get("school", "N/A"),
#                 "subject": entry.get("subject", "N/A"),
#                 "score": entry.get("score", 0),
#                 "PreviousLevel": entry.get("previousLevel", "N/A"),
#                 "CurrentLevel": entry.get("CurrentLevel", "N/A"),
#                 "last_updated": entry.get("LastUpdated", "N/A"),
#             })
#     return leaderboard_data

@router.get("/leaderboard")
async def get_leaderboard():
    try:
        # Fetch the latest 50 improvement logs, sorted by timestamp descending
        logs_cursor = leaderboard_collection.find().sort("timestamp", -1).limit(50)
        logs = []
        for log in logs_cursor:
            logs.append({
                "userId": log.get("userId"),
                "name": log.get("name"),
                "school": log.get("school"),
                "subject": log.get("subject"),
                "topic": log.get("topic"),
                "subtopic": log.get("subtopic"),
                "previous_level": log.get("previous_level"),
                "new_level": log.get("new_level"),
                "timestamp": log.get("timestamp").isoformat() if isinstance(log.get("timestamp"), datetime) else log.get("timestamp")
            })
        return {"leaderboard": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving leaderboard: {str(e)}")







