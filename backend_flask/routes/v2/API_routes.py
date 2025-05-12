from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, RootModel
from database.db import assessment_collection, create_goal ,class_tenth_collection 
from typing import Dict, Optional
import jwt as pyjwt
from typing import List

router = APIRouter(prefix="/v2", tags=["Auth"])

SECRET_KEY = "your_secret_key_here"  # Make sure this is the same as in your auth_utils.py
ALGORITHM = "HS256"

class LevelInfo(BaseModel):
    level: Optional[str] = None
    subtopics: Optional[Dict[str, "LevelInfo"]] = None

class SubjectLevels(RootModel[Dict[str, Dict[str, LevelInfo]]]):
    pass

class SelfAssessmentRequest(BaseModel):
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

@router.post("/self-assessment")
async def save_self_assessment(
    data: SelfAssessmentRequest,
    request: Request,
):
    user_id = request.headers.get("X-User-ID")
    token_payload = decode_token(request)

    if token_payload:
        user_id = token_payload.get("userId")

    if user_id:
        try:
            assessment_collection.update_one(
                {"userId": user_id},
                {
                    "$set": {
                        "levels": data.levels.model_dump(),
                    }
                },
                upsert=True,
            )
            return {"message": "Self-assessment saved successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=401, detail="Not authenticated")

@router.get("/self-assessment")
async def get_self_assessment(user=Depends(get_current_user)):
    try:
        user_id = user["userId"]
        data = assessment_collection.find_one({"userId": user_id}, {"_id": 0, "levels": 1})
        return {"levels": data["levels"] if data and "levels" in data else {}}
    except Exception as e:
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
            # Convert Pydantic model to a dictionary for database insertion
            goal_dict = goal_data.model_dump()
            goal_dict["userId"] = user_id  # Add the userId to the goal data
            create_goal.insert_one(goal_dict)  # Use insert_one
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
            goal["_id"] = str(goal["_id"])  # Convert ObjectId to string
            goals.append(goal)
        return {"goals": goals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving goals: {str(e)}")
    

