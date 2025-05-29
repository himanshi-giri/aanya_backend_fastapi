# backend_flask/routes/v2/leaderboard.py

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Optional
from datetime import datetime
from bson import ObjectId
import jwt as pyjwt
from database.db import leaderboard_collection, new_users_collection

router = APIRouter(prefix="/v2", tags=["Leaderboard_v1"])

SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"

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

@router.get("/leaderboard")
async def get_leaderboard():
    try:
        # Define the level order to calculate improvement scores
        level_order = {
            "Beginner": 1,
            "Developing": 2,
            "Proficient": 3,
            "Advanced": 4,
            "Mastery": 5
        }

        # Use MongoDB aggregation to get one improvement per user
        pipeline = [
            # Unwind the improvements array to create a document for each improvement
            {"$unwind": "$improvements"},
            # Lookup to join with new_users collection to get profilePhoto
            {
                "$lookup": {
                    "from": "users",  # Confirmed collection name
                    "localField": "userId",
                    "foreignField": "userId",
                    "as": "user_data"
                }
            },
            # Unwind user_data with preserveNullAndEmptyArrays to handle missing matches
            {
                "$unwind": {
                    "path": "$user_data",
                    "preserveNullAndEmptyArrays": True
                }
            },
            # Project the fields we need, including profilePhoto with fallback
            {
                "$project": {
                    "userId": 1,
                    "name": 1,
                    "school": 1,
                    "profilePhoto": {
                        "$ifNull": ["$user_data.profilePhoto", None]
                    },
                    "subject": "$improvements.subject",
                    "topic": "$improvements.topic",
                    "subtopic": "$improvements.subtopic",
                    "previous_level": "$improvements.previous_level",
                    "new_level": "$improvements.new_level",
                    "timestamp": "$improvements.timestamp",
                    "score": {
                        "$multiply": [
                            {
                                "$subtract": [
                                    {"$arrayElemAt": [
                                        [0, 1, 2, 3, 4, 5],
                                        {
                                            "$indexOfArray": [
                                                ["Beginner", "Developing", "Proficient", "Advanced", "Mastery"],
                                                "$improvements.new_level"
                                            ]
                                        }
                                    ]},
                                    {"$arrayElemAt": [
                                        [0, 1, 2, 3, 4, 5],
                                        {
                                            "$indexOfArray": [
                                                ["Beginner", "Developing", "Proficient", "Advanced", "Mastery"],
                                                "$improvements.previous_level"
                                            ]
                                        }
                                    ]}
                                ]
                            },
                            10
                        ]
                    }
                }
            },
            # Sort improvements for each user by score and timestamp
            {"$sort": {"score": -1, "timestamp": -1}},
            # Group by userId to get the top improvement per user
            {
                "$group": {
                    "_id": "$userId",
                    "userId": {"$first": "$userId"},
                    "name": {"$first": "$name"},
                    "school": {"$first": "$school"},
                    "profilePhoto": {"$first": "$profilePhoto"},
                    "subject": {"$first": "$subject"},
                    "topic": {"$first": "$topic"},
                    "subtopic": {"$first": "$subtopic"},
                    "previous_level": {"$first": "$previous_level"},
                    "new_level": {"$first": "$new_level"},
                    "timestamp": {"$first": "$timestamp"},
                    "score": {"$first": "$score"}
                }
            },
            # Sort users by score and timestamp
            {"$sort": {"score": -1, "timestamp": -1}},
            # Limit to top 20 users
            {"$limit": 20}
        ]

        # Execute the aggregation pipeline
        logs_cursor = leaderboard_collection.aggregate(pipeline)
        logs = []
        for log in logs_cursor:
            # Debug: Log if profilePhoto is missing for specific userId
            if log.get("userId") == "zyykq3za5a" and not log.get("profilePhoto"):
                print(f"Debug: No profilePhoto for userId zyykq3za5a, user_data: {log.get('user_data')}")
            logs.append({
                "userId": log.get("userId"),
                "name": log.get("name"),
                "school": log.get("school"),
                "profilePhoto": log.get("profilePhoto"),
                "subject": log.get("subject"),
                "topic": log.get("topic"),
                "subtopic": log.get("subtopic"),
                "previous_level": log.get("previous_level"),
                "new_level": log.get("new_level"),
                "timestamp": log.get("timestamp").isoformat() if isinstance(log.get("timestamp"), datetime) else log.get("timestamp"),
                "score": log.get("score")
            })

        return {"leaderboard": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving leaderboard: {str(e)}")