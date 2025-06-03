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

# Level configuration
LEVEL_ORDER = {
    "Beginner": 1,
    "Developing": 2,
    "Proficient": 3,
    "Advanced": 4,
    "Mastery": 5
}

# Reverse mapping for getting level name from number
LEVEL_NAMES = {v: k for k, v in LEVEL_ORDER.items()}
MAX_LEVEL = 5

def get_level_name(level_number: int) -> str:
    """Convert level number to level name"""
    return LEVEL_NAMES.get(level_number, "Beginner")

def get_level_number(level_name: str) -> int:
    """Convert level name to level number"""
    return LEVEL_ORDER.get(level_name, 1)

def get_next_level_info(current_level: int) -> tuple:
    """Get next level number and name, return None if at max level"""
    if current_level >= MAX_LEVEL:
        return None, None
    next_level = current_level + 1
    return next_level, get_level_name(next_level)

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

@router.post("/v2/create-goal")
async def create_new_goal(goal: Goal, user = Depends(get_current_user)):
    try:
        goal_data = goal.dict()
        goal_data["user_id"] = user["userId"]
        goal_data["created_at"] = datetime.now()
        goal_data["completed"] = False
        goal_data["progress"] = 0
        goal_data["status"] = "Not started"
        
        result = create_goal.insert_one(goal_data)
        
        return GoalResponse(
            success=True, 
            message="Goal created successfully", 
            goal_id=str(result.inserted_id)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating goal: {str(e)}")

@router.get("/v2/get-goals")
async def get_goals(user = Depends(get_current_user)):
    try:
        goals = list(create_goal.find({"user_id": user["userId"]}))
        
        # Convert ObjectId to string for JSON serialization
        for goal in goals:
            goal["_id"] = str(goal["_id"])
            goal["user_id"] = str(goal["user_id"])
            
             # Ensure status field exists - set default if missing
            if "status" not in goal:
                if goal.get("completed", False):
                    goal["status"] = "Successfully achieved"
                else:
                    goal["status"] = "Not started"
            
            # Ensure other required fields have defaults
            goal.setdefault("completed", False)
            goal.setdefault("progress", 0)
            
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

        # Get user's current level for this subject
        user_level_number = user.get("subject_levels", {}).get(subject, 1)
        current_level_name = get_level_name(user_level_number)
        
        # Check if user is already at max level
        if user_level_number >= MAX_LEVEL:
            raise HTTPException(
                status_code=400, 
                detail=f"You have already achieved the maximum level ({get_level_name(MAX_LEVEL)}) for {subject}. No further goals can be created."
            )
        
        # Get next level info
        target_level_number, target_level_name = get_next_level_info(user_level_number)
        
        if not target_level_number:
            raise HTTPException(
                status_code=400,
                detail=f"You are already at the maximum level for {subject}"
            )

        print(f"📘 Subject: {subject} | Topic: {topic} | Current Level: {current_level_name} ({user_level_number}) | Target Level: {target_level_name} ({target_level_number})")

        # Prepare Gemini prompt with level names
        prompt = f"""
        Generate 10 multiple-choice questions about {subject} on the topic of {topic} for class 10th student. 
        These questions should be at {target_level_name} difficulty level (progressing from {current_level_name} to {target_level_name}).
        
        Level context:
        - Beginner: Basic concepts and definitions
        - Developing: Understanding with simple applications
        - Proficient: Clear understanding with moderate applications
        - Advanced: Deep understanding with complex applications
        - Mastery: Expert level with advanced problem-solving
        
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
                "difficulty": "{target_level_name}"
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
            "current_level": current_level_name,
            "current_level_number": user_level_number,
            "target_level": target_level_name,
            "target_level_number": target_level_number,
            "is_max_level": target_level_number >= MAX_LEVEL
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

         # Verify user owns this goal - Fix the field name issue
        goal_user_id = goal.get("user_id")  # This should match what you store during creation
        current_user_id = user["userId"]

        # Verify user owns this goal
        if str(goal.get("user_id")) != user["userId"]:
            print(f"Goal ownership mismatch: goal user_id={goal.get('user_id')}, user userId={user['userId']}")
            # Continue anyway since we want to update the goal
        
        score = data.get("score", 0)  # Score out of 100
        status = data.get("status", "")  # Get status from request
        subject = goal.get("subject")
        topic = goal.get("topic")
        
        # Determine goal completed status based on score
        goal_completed = score > 80
        
        # If no status provided, generate one based on score
        if not status:
            if score > 80:
                status = "Successfully achieved"
            elif score >= 50:
                status = "Partially achieved"
            else:
                status = "Not achieved"

        goal_completed = (score >= 90 and status == "Successfully achieved")        
        
        # Update goal progress - correct field names
        update_data = {
            "progress": score, 
            "completed": goal_completed,
            "status": status,
            "completed_at": datetime.now(),
            "final_score": score  
        }
         # Only add completed_at if the goal is actually completed
        if not goal_completed:
            # Remove completed_at for failed attempts, but keep attempt_at
            update_data["attempt_at"] = datetime.now()
            del update_data["completed_at"]

        print(f"Updating goal {goal_id} with data: {update_data}")
        
        goal_update_result = create_goal.update_one(
            {"_id": ObjectId(goal_id)},
            {"$set": update_data}
        )
        if goal_update_result.modified_count == 0:
            print("Warning: Goal update didn't modify any document")
        
        # Level up logic - only if goal is successfully achieved
        level_up_occurred = False
        previous_level_name = None
        new_level_name = None
        reached_max_level = False
        
        if goal_completed and subject:
            try:
                # Get current user data to check current level
                current_user_data = new_users_collection.find_one({"userId": current_user_id})
                if not current_user_data:
                    raise Exception("User not found for level update")
                
                # Get current subject levels
                current_subject_levels = current_user_data.get("subject_levels", {})
                current_level_number = current_subject_levels.get(subject, 1)  # Default to level 1
                previous_level_name = get_level_name(current_level_number)
                
                # Check if already at max level
                if current_level_number >= MAX_LEVEL:
                    print(f"User already at maximum level ({get_level_name(MAX_LEVEL)}) for {subject}")
                    reached_max_level = True
                else:
                    new_level_number = current_level_number + 1
                    new_level_name = get_level_name(new_level_number)
                    
                    # Cap at maximum level
                    if new_level_number > MAX_LEVEL:
                        new_level_number = MAX_LEVEL
                        new_level_name = get_level_name(MAX_LEVEL)
                        reached_max_level = True
                    
                    print(f"Attempting to level up user in {subject}: {previous_level_name} ({current_level_number}) -> {new_level_name} ({new_level_number})")
                    
                    # Update user's level for this subject
                    subject_key = f"subject_levels.{subject}"
                    user_update_result = new_users_collection.update_one(
                        {"userId": current_user_id},
                        {"$set": {subject_key: new_level_number}}
                    )
                    
                    if user_update_result.modified_count > 0:
                        level_up_occurred = True
                        print(f"✅ Successfully updated user level for {subject} to {new_level_name} ({new_level_number})")
                        
                        # Optional: Log the level up event for analytics
                        level_up_log = {
                            "user_id": current_user_id,
                            "subject": subject,
                            "topic": topic,
                            "previous_level": previous_level_name,
                            "previous_level_number": current_level_number,
                            "new_level": new_level_name,
                            "new_level_number": new_level_number,
                            "goal_id": goal_id,
                            "score_achieved": score,
                            "reached_max_level": reached_max_level,
                            "timestamp": datetime.now()
                        }
                        
                        # You can create a separate collection for level up logs if needed
                        # level_up_collection.insert_one(level_up_log)
                        
                    else:
                        print("Warning: User level update didn't modify any document")
                    
            except Exception as level_error:
                print(f"Error updating user level: {str(level_error)}")
                # Don't fail the entire request if level update fails
                # The goal completion should still succeed
        
        # Prepare response
        response_data = {
            "success": True,
            "message": f"Goal completed successfully: {status}",
            "goal_completed": goal_completed,
            "leveled_up": level_up_occurred,
            "status": status,
            "score": score,
            "can_reattempt": status == "Not achieved",
            "reached_max_level": reached_max_level
        }
        
        # Include level information if level up occurred
        if level_up_occurred and new_level_name:
            response_data.update({
                "subject": subject,
                "previous_level": previous_level_name,
                "new_level": new_level_name,
                "level_up_message": f"Congratulations! You've advanced from {previous_level_name} to {new_level_name} in {subject}!"
            })
            
            # Add special message if max level reached
            if reached_max_level:
                response_data["max_level_message"] = f"🎉 Amazing! You've reached the highest level ({new_level_name}) in {subject}!"
        
        return response_data
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error in complete_goal: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error completing goal: {str(e)}")

@router.get("/v2/user-levels")
async def get_user_levels(user = Depends(get_current_user)):
    """Get user's current levels for all subjects"""
    try:
        user_levels = user.get("subject_levels", {})
        formatted_levels = {}
        
        for subject, level_number in user_levels.items():
            formatted_levels[subject] = {
                "level_number": level_number,
                "level_name": get_level_name(level_number),
                "is_max_level": level_number >= MAX_LEVEL,
                "next_level": get_level_name(level_number + 1) if level_number < MAX_LEVEL else None
            }
        
        return {
            "success": True,
            "levels": formatted_levels,
            "level_system": {
                "max_level": MAX_LEVEL,
                "max_level_name": get_level_name(MAX_LEVEL),
                "all_levels": LEVEL_NAMES
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user levels: {str(e)}")