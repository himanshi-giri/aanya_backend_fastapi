from operator import ne
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, RootModel

from database.db import assessment_collection, practice_assessment_collection, create_goal, leaderboard_collection, class_tenth_collection, new_users_collection

from typing import Dict, Optional
import jwt as pyjwt
from typing import List
from datetime import datetime

router = APIRouter(prefix="/v2", tags=["Auth"])

SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"

class LevelInfo(BaseModel):
    level: Optional[str] = None
    subtopics: Optional[Dict[str, "LevelInfo"]] = None
    lastUpdated: Optional[datetime] = None

class SubjectLevels(RootModel[Dict[str, Dict[str, LevelInfo]]]):
    pass

class SelfAssessmentRequest(BaseModel):
    levels: SubjectLevels

class PracticeAssessmentRequest(BaseModel):
    levels: SubjectLevels

class CreateGoalRequest(BaseModel):
    subject: str
    topic: str
    details: str
    testDate: str
    reminder: str
    isSkillImprovement: bool

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

# Map for comparing levels
level_order = {
    "Beginner": 1,
    " Developing": 2,
    "Proficient": 3,
    "Advanced": 4,
    "Mastery": 5
}

# Compare new vs old and log improvements
def compare_and_log_improvements(user_id, user_name, school, old_data, new_data, collection_name):
    def traverse(subject, topic, old, new, path=[]):
        improvements = []

        if old is None or new is None:
            return improvements

        old_level = old.get("level")
        new_level = new.get("level")

        if old_level and new_level and level_order.get(new_level, 0) > level_order.get(old_level, 0):
            improvements.append({
                "subject": subject,
                "topic": topic,
                "subtopic": " > ".join(path) if path else None,
                "previous_level": old_level,
                "new_level": new_level,
                "timestamp": datetime.utcnow()
            })

        old_subs = old.get("subtopics")
        new_subs = new.get("subtopics")

        if old_subs and new_subs:
            for key in new_subs:
                if key in old_subs:
                    improvements += traverse(subject, topic, old_subs[key], new_subs[key], path + [key])

        return improvements

    improvements = []
    for subject, topics in new_data.items():
        for topic, new_topic_data in topics.items():
            old_topic_data = old_data.get(subject, {}).get(topic, {})
            improvements += traverse(subject, topic, old_topic_data, new_topic_data)

    if improvements:
        leaderboard_collection.update_one(
            {"userId": user_id},
            {
                "$set": {
                    "name": user_name,
                    "school": school,
                    "lastUpdated": datetime.utcnow()
                },
                "$push": {
                    f"{collection_name}_improvements": {"$each": improvements}
                },
                "$inc": {
                    f"total_{collection_name}_improvements": len(improvements)
                }
            },
            upsert=True
        )

@router.post("/self-assessment")
async def save_self_assessment(data: SelfAssessmentRequest, request: Request):
    user = decode_token(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user["userId"]
    user_doc = new_users_collection.find_one({"userId": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail=f"User with userId {user_id} not found in new_users_collection")

    user_name = user_doc.get("fullName", "Unknown")
    school = user_doc.get("school", " ")

    new_levels = data.levels.model_dump()

    current_time = datetime.utcnow()
    for subject, topics in new_levels.items():
        for topic, level_info in topics.items():
            level_info["lastUpdated"] = current_time
            if level_info.get("subtopics"):
                for subtopic, subtopic_info in level_info["subtopics"].items():
                    subtopic_info["lastUpdated"] = current_time

    previous_record = assessment_collection.find_one({"userId": user_id})
    previous_levels = previous_record.get("levels", {}) if previous_record else {}

    try:
        assessment_collection.update_one(
            {"userId": user_id},
            {"$set": {
                "levels": new_levels
            }},
            upsert=True
        )

        compare_and_log_improvements(user_id, user_name, school, previous_levels, new_levels, "self_assessment")

        return {"message": "Self-assessment updated and improvements logged"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/self-assessment")
async def get_self_assessment(user=Depends(get_current_user)):
    try:
        user_id = user["userId"]
        data = assessment_collection.find_one({"userId": user_id}, {"_id": 0, "levels": 1})
        return {
            "levels": data["levels"] if data and "levels" in data else {}
        }
    except Exception as e:
        print(f"Error in get_self_assessment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/practice-assessment")
async def save_practice_assessment(data: PracticeAssessmentRequest, request: Request):
    user = decode_token(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user["userId"]
    user_doc = new_users_collection.find_one({"userId": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail=f"User with userId {user_id} not found in new_users_collection")

    user_name = user_doc.get("fullName", "Unknown")
    school = user_doc.get("school", " ")

    new_levels = data.levels.model_dump()

    current_time = datetime.utcnow()
    for subject, topics in new_levels.items():
        for topic, level_info in topics.items():
            level_info["lastUpdated"] = current_time
            if level_info.get("subtopics"):
                for subtopic, subtopic_info in level_info["subtopics"].items():
                    subtopic_info["lastUpdated"] = current_time

    previous_record = practice_assessment_collection.find_one({"userId": user_id})
    previous_levels = previous_record.get("levels", {}) if previous_record else {}

    try:
        practice_assessment_collection.update_one(
            {"userId": user_id},
            {"$set": {
                "levels": new_levels
            }},
            upsert=True
        )

        compare_and_log_improvements(user_id, user_name, school, previous_levels, new_levels, "practice_assessment")

        return {"message": "Practice-assessment updated and improvements logged"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/practice-assessment")
async def get_practice_assessment(user=Depends(get_current_user)):
    try:
        user_id = user["userId"]
        data = practice_assessment_collection.find_one({"userId": user_id}, {"_id": 0, "levels": 1})
        return {
            "levels": data["levels"] if data and "levels" in data else {}
        }
    except Exception as e:
        print(f"Error in get_practice_assessment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-goals")
async def save_createGoal(
    goal_data: CreateGoalRequest,
    request: Request,
):
    user_id = request.headers.get("X-User-ID")
    token_payload = decode_token(request)

    if token_payload:
        user_id = token_payload.get("userId")

    if user_id:
        try:
            goal_dict = goal_data.model_dump()
            goal_dict["userId"] = user_id
            create_goal.insert_one(goal_dict)
            return {"message": "Goal created successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create goal: {str(e)}")
    else:
        raise HTTPException(status_code=401, detail="Not authenticated")

@router.get("/class-tenth")
async def get_class_tenth():
    try:
        syllabus_data = class_tenth_collection.find_one({}, {"_id": 0})
        if syllabus_data:
            return syllabus_data
        else:
            raise HTTPException(status_code=404, detail="Class tenth syllabus data not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching class tenth syllabus: {str(e)}")

@router.get("/get-goals")
async def get_user_goals(user=Depends(get_current_user)):
    try:
        user_id = user["userId"]
        goals_cursor = create_goal.find({"userId": user_id})
        goals = []
        for goal in goals_cursor:
            goal["_id"] = str(goal["_id"])
            goals.append(goal)
        return {"goals": goals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving goals: {str(e)}")