from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from bson import ObjectId
import json
import uuid
import google.generativeai as genai
import os
from database.db import challenges_collection, new_users_collection,assessment_collection
import re
from fastapi.responses import JSONResponse
from bson.errors import InvalidId
from pymongo.collection import Collection


router = APIRouter(prefix="/play", tags=["Play With Friend"])

LEVELS = ['beginner', 'developing', 'proficient', 'master', 'advance']

def calculate_challenge_level_from_ids(creator_id: str, opponent_id: str, subject: str, assessment_collection: Collection) -> str:
    # Helper to fetch user's level for the subject
    def get_user_level(user_id: str) -> str:
        record = assessment_collection.find_one({"userId": user_id})
        print(record,"record/n",)
        if not record:
            raise HTTPException(status_code=404, detail=f"Assessment data not found for user {user_id}")
        levels = record.get("levels", {})
        subject_level = levels.get(subject, {}).get("level")
        if subject_level not in LEVELS:
            raise HTTPException(status_code=400, detail=f"Invalid or missing level for {subject} in user {user_id}")
        return subject_level

    # Handle guest opponent
    if opponent_id == 'Null':
        return get_user_level(creator_id)

    # Fetch levels
    creator_level = get_user_level(creator_id)
    opponent_level = get_user_level(opponent_id)

    c_idx = LEVELS.index(creator_level)
    o_idx = LEVELS.index(opponent_level)

    if c_idx == o_idx:
        return LEVELS[min(c_idx + 1, len(LEVELS) - 1)]

    avg_idx = (c_idx + o_idx) // 2
    return LEVELS[avg_idx]
# Configure Gemini API
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class ChallengeCreate(BaseModel):
    creatorId: str
    subject: str
    topic: str
    level: str
    opponentId: Optional[str] = None
    subtopic: Optional[str] = None
    mode: str  # "sync" or "async"


class JoinChallenge(BaseModel):
    inviteCode: str
    userId: str

class StartChallengeRequest(BaseModel):
    pass

class AnswerSubmission(BaseModel):
    userId: str
    questionIndex: int
    answer: str

class Question(BaseModel):
    question: str
    options: List[str]
    answer: str

def generate_sample_questions(subject: str, topic: str, level: str = "medium") -> List[Dict]:
    if subject == "Mathematics" and topic == "Algebra":
        return [
            {"question": "What is the value of x in the equation 3x + 2 = 8?", "options": ["1", "2", "3", "4"], "answer": "2"},
            {"question": "Simplify the expression: 5y - 2y + 7y", "options": ["9y", "10y", "12y", "14y"], "answer": "10y"}
        ]
    elif subject == "Science" and topic == "Physics":
        return [
            {"question": "Which law states that energy cannot be created or destroyed?", "options": ["Newton's First Law", "Newton's Second Law", "Law of Conservation of Energy", "Ohm's Law"], "answer": "Law of Conservation of Energy"},
            {"question": "What is the unit of electric current?", "options": ["Volt", "Ohm", "Ampere", "Watt"], "answer": "Ampere"}
        ]
    else:
        return [{"question": f"No dummy questions for {subject} - {topic}"}]

async def generate_questions_from_gemini(subject: str, topic: str, level: str = "medium", subtopic: Optional[str] = None) -> List[Dict]:
    context = f"{subtopic} under {topic}" if subtopic else topic
    prompt = (
        f"Generate 10 multiple-choice quiz question about {context} in {subject} at a {level} difficulty level. "
        "Return the result in the following JSON format:\n"
        "[\n"
        "  {\n"
        "    \"question\": \"<Your question here>\",\n"
        "    \"options\": [\"A\", \"B\", \"C\", \"D\"],\n"
        "    \"answer\": \"<Correct option text>\"\n"
        "  }\n"
        "]\n"
        "Do not include any explanation or extra text—only valid JSON."
    )

    try:
        response = model.generate_content(prompt, generation_config={"temperature": 0.7, "max_output_tokens": 2048})
        response.resolve()
        if response.text:
            try:
                cleaned_text = re.sub(r"^```json|```$", "", response.text.strip()).strip()
                questions = json.loads(cleaned_text)
                return questions
            except json.JSONDecodeError:
                return [{"question": f"Invalid JSON format for {subject} - {context}"}]
        else:
            return [{"question": f"Failed to generate question for {subject} - {context}"}]
    except Exception as e:
        return [{"question": f"Error generating question for {subject} - {context}"}]

def generate_unique_invite_code():
    while True:
        code = uuid.uuid4().hex[:6].upper()
        if not challenges_collection.find_one({"inviteCode": code}):
            return code


# @router.post("/challenges")
# async def create_challenge(data: ChallengeCreate):
#     challenge_id = str(uuid.uuid4())
#     invite_code = generate_unique_invite_code() if not data.opponentId else None
#     questions = await generate_questions_from_gemini(data.subject, data.topic, data.level, data.subtopic)

#     opponent = new_users_collection.find_one({"_id": ObjectId(data.opponentId)}) if data.opponentId else None
#     #print(opponent)
#     if opponent:
#         print(opponent.get("userId"))

#     challenge_doc = {
#         "_id": challenge_id,
#         "creator": data.creatorId,
#         "opponent": opponent.get("userId"),
#         "subject": data.subject,
#         "topic": data.topic,
#         "level": data.level,
#         "questions": questions,
#         "answers": {},
#         "inviteCode": invite_code,
#         "status": "waiting"
#     }

#     challenges_collection.insert_one(challenge_doc)
#     new_users_collection.update_one(
#         {"userId": data.creatorId},
#         {"$addToSet": {"challenges": challenge_id}}
#     )

#     if data.opponentId:
#         new_users_collection.update_one(
#             {"_id": data.opponentId},
#             {"$addToSet": {"challenges": challenge_id}}
#         )

#     return {
#         "challengeId": challenge_id,
#         "inviteCode": invite_code,
#         "status": challenge_doc["status"]
#     }

@router.post("/challenges")
async def create_challenge(data: ChallengeCreate):
    challenge_id = str(uuid.uuid4())
    invite_code = generate_unique_invite_code() if data.mode == "async" else None

    opponent_user_id = None
    if data.opponentId:
        opponent = new_users_collection.find_one({"_id": ObjectId(data.opponentId)})
        if opponent:
            opponent_user_id = opponent.get("userId")
        else:
            raise HTTPException(status_code=404, detail="Opponent not found")
    # print(opponent_user_id)
    # level = calculate_challenge_level_from_ids(
    # creator_id=data.creatorId,
    # opponent_id=opponent_user_id,
    # subject="Mathematics",
    # assessment_collection=assessment_collection
#)
    #print(level)
    # Generate questions
    questions = await generate_questions_from_gemini(
        data.subject, data.topic, data.level, data.subtopic
    )

   
    challenge_doc = {
        "_id": challenge_id,
        "creator": data.creatorId,
        "opponent": opponent_user_id,
        "subject": data.subject,
        "topic": data.topic,
        "level": data.level,
        "subtopic": data.subtopic,
        "questions": questions,
        "answers": {},
        "inviteCode": invite_code,
        "mode": data.mode,
        "status": "waiting"
    }

    # Insert the challenge
    challenges_collection.insert_one(challenge_doc)

    # Add challenge ID to creator
    new_users_collection.update_one(
        {"userId": data.creatorId},
        {"$addToSet": {"challenges": challenge_id}}
    )

    # Add challenge ID to opponent, if any
    if data.opponentId:
        new_users_collection.update_one(
            {"_id": ObjectId(data.opponentId)},
            {"$addToSet": {"challenges": challenge_id}}
        )

    return {
        "challengeId": challenge_id,
        "inviteCode": invite_code,
        "status": challenge_doc["status"]
    }

@router.get("/challenges/{challenge_id}")
def get_challenge(challenge_id: str):
    try:
        challenge = challenges_collection.find_one({"_id": challenge_id})
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid challenge ID format")

    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    response_data = {
        "mode": challenge.get("mode"),
        "inviteCode": challenge.get("inviteCode", ""),
        "status": challenge.get("status"),
    }

    return JSONResponse(content=response_data)


@router.post("/challenges/join")
async def join_challenge(data: JoinChallenge):
    challenge = challenges_collection.find_one({"inviteCode": data.inviteCode})
    if not challenge:
        raise HTTPException(status_code=404, detail="Invite code not found.")
    if challenge['opponent'] is not None:
        raise HTTPException(status_code=400, detail="Challenge already has an opponent.")

    challenges_collection.update_one({"_id": challenge["_id"]}, {"$set": {"opponent": data.userId, "status": "ready"}})
    new_users_collection.update_one({"userId": data.userId}, {"$addToSet": {"challenges": challenge['_id']}})

    return {"challengeId": challenge['_id']}

# @router.post("/challenges/{challenge_id}/start")
# async def start_challenge(challenge_id: str):
#     challenge = challenges_collection.find_one({"_id": challenge_id})
#     if not challenge:
#         raise HTTPException(status_code=404, detail="Challenge not found.")
#     if not challenge['opponent']:
#         raise HTTPException(status_code=400, detail="Waiting for opponent to join.")

#     # ✅ Update status to "started"
#     challenges_collection.update_one({"_id": challenge_id}, {"$set": {"status": "started"}})

#     return {"questions": challenge['questions']}

@router.post("/challenges/{challenge_id}/start")
async def start_challenge(challenge_id: str):
    challenge = challenges_collection.find_one({"_id": challenge_id})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found.")

    # ✅ Update status to "started" regardless of opponent status
    challenges_collection.update_one({"_id": challenge_id}, {"$set": {"status": "started"}})

    return {"questions": challenge['questions']}


# @router.post("/challenges/{challenge_id}/answer")
# async def submit_answer(challenge_id: str, data: AnswerSubmission):
#     challenge = challenges_collection.find_one({"_id": challenge_id})
#     if not challenge:
#         raise HTTPException(status_code=404, detail="Challenge not found.")
#     if data.userId not in [challenge['creator'], challenge['opponent']]:
#         raise HTTPException(status_code=403, detail="Not a participant.")

#     user_answers = challenge.setdefault("answers", {}).setdefault(data.userId, {})
#     user_answers[str(data.questionIndex)] = data.answer

#     challenges_collection.update_one({"_id": challenge_id}, {"$set": {f"answers.{data.userId}": user_answers}})
#     return {"message": "Answer recorded."}

from fastapi import Request

@router.post("/challenges/{challenge_id}/answer")
async def submit_answer(challenge_id: str, data: AnswerSubmission, request: Request):
    challenge = challenges_collection.find_one({"_id": challenge_id})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found.")
    print(data.userId)
    # If user is guest (e.g., guest_6B57FA), allow only in async mode
    is_guest = data.userId.startswith("guest")
    if is_guest:
        if challenge.get("mode") != "async":
            raise HTTPException(status_code=403, detail="Guests can only participate in async challenges.")
    elif data.userId not in [challenge.get("creator"), challenge.get("opponent")]:
        raise HTTPException(status_code=403, detail="Not a participant.")

    # Store answers
    user_answers = challenge.setdefault("answers", {}).setdefault(data.userId, {})
    user_answers[str(data.questionIndex)] = data.answer

    challenges_collection.update_one(
        {"_id": challenge_id},
        {"$set": {f"answers.{data.userId}": user_answers}}
    )
    return {"message": "Answer recorded."}

# @router.get("/challenges/{challenge_id}/result")
# async def get_result(challenge_id: str):
#     challenge = challenges_collection.find_one({"_id": challenge_id})
#     if not challenge:
#         raise HTTPException(status_code=404, detail="Challenge not found.")

#     questions = challenge['questions']
#     scores = {}

#     for user in [challenge.get('creator'), challenge.get('opponent')]:
#         if user:
#             answers = challenge['answers'].get(user, {})
#             score = sum(1 for idx, q in enumerate(questions) if str(answers.get(str(idx))) == str(q['answer']))
#             scores[user] = score

#     winner = None
#     if scores.get(challenge.get('creator')) > scores.get(challenge.get('opponent')):
#         winner = challenge.get('creator')
#     elif scores.get(challenge.get('creator')) < scores.get(challenge.get('opponent')):
#         winner = challenge.get('opponent')
#     else:
#         winner = "Draw"

#     return {"scores": scores, "winner": winner}

@router.get("/challenges/{challenge_id}/result")
async def get_result(challenge_id: str):
    challenge = challenges_collection.find_one({"_id": challenge_id})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found.")

    creator_id = challenge.get('creator')
    opponent_id = challenge.get('opponent')
    questions = challenge['questions']
    answers = challenge.get('answers', {})

    # Check if both users have submitted their answers
    if not (creator_id in answers and opponent_id in answers):
        return {
            "status": "waiting",
            "message": "Opponent hasn't completed the challenge yet."
        }

    # Helper function to get user handle by user ID
    def get_handle(user_id):
        user = new_users_collection.find_one({"userId": user_id})
        return user.get('handle') if user else user_id  # fallback to userId if no handle

    creator_handle = get_handle(creator_id)
    opponent_handle = get_handle(opponent_id)

    # Calculate scores
    scores = {}
    for user_id, handle in [(creator_id, creator_handle), (opponent_id, opponent_handle)]:
        user_answers = answers.get(user_id, {})
        score = sum(
            1 for idx, q in enumerate(questions)
            if str(user_answers.get(str(idx))) == str(q['answer'])
        )
        scores[handle] = score  # Use handle as key here

    # Determine winner by handle
    if scores[creator_handle] > scores[opponent_handle]:
        winner = creator_handle
    elif scores[creator_handle] < scores[opponent_handle]:
        winner = opponent_handle
    else:
        winner = "Draw"

    return {
        "status": "complete",
        "scores": scores,
        "winner": winner
    }

@router.get("/challenges/user/{user_id}")
async def get_user_challenges(user_id: str):
    challenges_cursor = challenges_collection.find({
        "$or": [
            {"creator": user_id},
            {"opponent": user_id}
        ]
    })
    challenges_list = [
        {"id": str(ch["_id"]), **{k: v for k, v in ch.items() if k != "_id"}} for ch in challenges_cursor
    ]
    return {"challenges": challenges_list}

@router.get("/challenges/{challenge_id}/status")
async def get_challenge_status(challenge_id: str):
    try:
        challenge = challenges_collection.find_one({"_id": challenge_id})

        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found")

        return {
            "status": challenge.get("status", "waiting"),
            "creatorId": challenge.get("creator") or challenge.get("creatorId"),
            "opponentId": challenge.get("opponent") or challenge.get("opponentId"),
            "mode": challenge.get("mode", "sync")
        }

    except Exception as e:
        # Log actual error if needed
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/challenges/{challenge_id}/status")
async def update_challenge_status(challenge_id: str, payload: dict):
    try:
        status = payload.get("status")
        if status not in ["pending", "ready", "in-progress", "completed"]:
            raise HTTPException(status_code=400, detail="Invalid status")

        result = challenges_collection.update_one(
            {"_id": challenge_id},
            {"$set": {"status": status}}
        )
        print(result)
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Challenge not found or status unchanged")

        return {"message": "Status updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

