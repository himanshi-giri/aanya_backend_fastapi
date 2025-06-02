from fastapi import FastAPI,APIRouter, HTTPException, Depends, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, List, Optional
import jwt
from datetime import datetime, timedelta
import os
import google.generativeai as genai
from pydantic import BaseModel
from bson import ObjectId
import json
from database.db import users_collection, create_goal,new_users_collection

# Initialize FastAPI app
router = APIRouter(prefix="/api", tags=["Goal Practise"])


# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise Exception("Gemini API key not found in environment variables")

genai.configure(api_key=GEMINI_API_KEY)

# Security
security = HTTPBearer()
JWT_SECRET = os.getenv("SECRET_KEY", "your-secret-key")  # Use environment variable in production
JWT_ALGORITHM = "HS256"

# Pydantic models
class Goal(BaseModel):
    subject: str
    topic: str
    details: Optional[str] = None
    testDate: str
    reminder: str
    
class GoalResponse(BaseModel):
    success: bool
    message: str
    goal_id: Optional[str] = None

class Question(BaseModel):
    questionText: str
    options: List[str] 
    correctAnswer: int
    explanation: str
    difficulty: str

class QuestionsResponse(BaseModel):
    success: bool
    questions: List[Question]
    goalDetails: Dict

# Helper function to decode JWT token
def decode_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token format")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")

# Get the current user from the token
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    print(" Raw token received:", token)  # Debug log

    try:
        payload = decode_token(token)
        print(" Decoded payload:", payload)
    except Exception as e:
        print(" Token decode failed:", str(e))
        raise HTTPException(status_code=401, detail="Invalid token structure or signature")

    user_id = payload.get("userId")
    print(" Extracted userId from payload:", user_id)

    if not user_id:
        raise HTTPException(status_code=401, detail="userId missing from token payload")

    user = new_users_collection.find_one({"userId": user_id})
    print(" User found in DB:", user)

    if not user:
        raise HTTPException(status_code=404, detail="User not found in database")

    return user

@router.get("/v2/get-goals")
async def get_goals(user = Depends(get_current_user)):
    try:
        goals = list(create_goal.find({"user_id": user["userId"]}))
        
        # Convert ObjectId to string for JSON serialization
        for goal in goals:
            goal["_id"] = str(goal["_id"])
            goal["user_id"] = str(goal["user_id"])
        
        return {"success": True, "goals": goals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching goals: {str(e)}")

@router.get("/v2/start-goal/{goal_id}")
async def start_goal(goal_id: str, user = Depends(get_current_user)):
    try:
        print(f"\n [START] Looking up goal ID: {goal_id}")
        
        # Ensure valid ObjectId
        try:
            goal_object_id = ObjectId(goal_id)
        except Exception as e:
            print(f" Invalid goal_id: {e}")
            raise HTTPException(status_code=400, detail="Invalid goal ID format")

        # Fetch goal from DB
        goal = create_goal.find_one({"_id": goal_object_id, "userId": user["userId"]})
        if not goal:
            print(" Goal not found or doesn't belong to user")
            raise HTTPException(status_code=404, detail="Goal not found")

        print(" Goal found in DB:", goal)

        # Defensive check for required fields
        subject = goal.get("subject")
        topic = goal.get("topic")

        if not subject or not topic:
            print(" Missing 'subject' or 'topic' in goal")
            raise HTTPException(status_code=500, detail="Goal is missing subject or topic")

        user_level = user.get("subject_levels", {}).get(subject, 1)
        target_level = user_level + 1

        print(f"📘 Subject: {subject} | Topic: {topic} | Current Level: {user_level} | Target Level: {target_level}")

        # Prepare Gemini prompt
        prompt = f"""
        Generate 10 multiple-choice questions about {subject} on the topic of {topic} for class 10th student. 
        These questions should be at level {target_level} difficulty (where 1 is beginner and 10 is expert).
        
        Each question should have:
        1. A clear question statement
        2. Four possible answers (A, B, C, D)
        3. The index of the correct answer (0 for A, 1 for B, 2 for C, 3 for D)
        4. A detailed explanation of why the answer is correct
        
        Format the response as a JSON array of question objects with the following structure:
        [
            {{
                "questionText": "Question text here",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correctAnswer": 0,
                "explanation": "Explanation here",
                "difficulty": "{target_level}"
            }}
        ]
        
        Format the response as a **valid JSON array only**.
        """

        print(" Sending prompt to Gemini...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)

        raw_text = response.text.strip()
        print(" Raw Gemini Response:\n", raw_text[:500])  # Print a preview

        # Strip markdown if present
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:].strip()
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3].strip()

        # Try parsing response JSON
        try:
            questions_json = json.loads(raw_text)
            print(f"Parsed {len(questions_json)} questions from Gemini")

        except json.JSONDecodeError as e:
            print("JSON decode error:", e)
            raise HTTPException(status_code=500, detail="Gemini returned invalid JSON format")

        goal_details = {
            "_id": str(goal["_id"]),
            "subject": subject,
            "topic": topic,
            "details": goal.get("details", ""),
            "current_level": user_level,
            "target_level": target_level
        }

        return {
            "success": True,
            "questions": questions_json,
            "goalDetails": goal_details
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print("Unhandled error in start_goal:", e)
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {str(e)}")


@router.post("/v2/complete-goal/{goal_id}")
async def complete_goal(
    goal_id: str, 
    data: Dict = Body(...),
    user = Depends(get_current_user)
):
    try:
        goal = create_goal.find_one({"_id": ObjectId(goal_id)})
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
            
        # Verify user owns this goal
        if str(goal.get("user_id")) != user["userId"]:
            print(f"Goal ownership mismatch: goal user_id={goal.get('user_id')}, user userId={user['userId']}")
            # Continue anyway since we want to update the goal
        
        score = data.get("score", 0)  # Score out of 100
        status = data.get("status", "")  # Get status from request
        subject = goal.get("subject")
        
        # Determine goal completed status based on score
        goal_completed = score >= 90
        
        # If no status provided, generate one based on score
        if not status:
            if score >=90:
                status = "Successfully achieved"
            elif score >= 50:
                status = "Partially achieved"
            else:
                status = "Not achieved"
        
        # Update goal progress - correct field names
        update_data = {
            "progress": score, 
            "completed": goal_completed,
            "status": status,
            "completed_at": datetime.now()
        }
        
        print(f"Updating goal {goal_id} with data: {update_data}")
        
        create_goal.update_one(
            {"_id": ObjectId(goal_id)},
            {"$set": update_data}
        )
        
        # If score is good enough, consider leveling up the user in this subject
        level_up = score >= 90
        if level_up:
            current_level = user.get("subject_levels", {}).get(subject, 1)
            
            # Update user's level for this subject
            try:
                subject_key = f"subject_levels.{subject}"
                new_users_collection.update_one(
                    {"userId": user["userId"]},
                    {"$set": {subject_key: current_level + 1}}
                )
                print(f"Updated user level for {subject} to {current_level + 1}")
            except Exception as e:
                print(f"Error updating user level: {str(e)}")
                # Continue execution even if this fails
        
        return {
            "success": True,
            "message": "Goal progress updated",
            "leveled_up": level_up,
            "status": status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error completing goal: {str(e)}")
