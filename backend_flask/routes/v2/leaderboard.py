from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from typing import  List, Dict, Optional
from datetime import datetime
from bson import ObjectId
from database.db import  leaderboard_collection, new_users_collection

router = APIRouter(prefix="/v2", tags=["Leaderboard"])


# route for getting leaderboard info from leaderboard collection and user collection
 
@router.get("/leaderboard")
async def get_leaderboard():
    leaderboard_data = []
    leaderboard_entries = leaderboard_collection.find().sort("score", -1)

    for entry in leaderboard_entries:
        user = new_users_collection.find_one({"_id": ObjectId(entry["user_id"])})
        if user:
            leaderboard_data.append({
                "name": user["name"],
                "school": user["school"],
                "subject": entry["subject"],
                "score": entry["score"],
                "PreviousLevel":entry["previousLevel"],
                "CurrentLevel": entry["CurrentLevel"],
                "last_updated": entry["LastUpdated"],
            })
    return leaderboard_data




