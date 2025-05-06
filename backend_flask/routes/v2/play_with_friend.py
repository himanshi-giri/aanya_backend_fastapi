from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
import requests

router = APIRouter(prefix="/play", tags=["Play With Friend"])

# In-memory data store (simulate database)
challenges = {}

# ------------------ Models ------------------

class ChallengeCreate(BaseModel):
    creatorId: str
    subject: str
    topic: str
    level: str

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
    answer: str  # for now; in real game you might hide this

# ------------------ Routes ------------------

@router.post("/challenges")
def create_challenge(data: ChallengeCreate):
    challenge_id = str(uuid.uuid4())
    invite_code = uuid.uuid4().hex[:6].upper()
    
    challenges[challenge_id] = {
        "creator": data.creatorId,
        "opponent": None,
        "subject": data.subject,
        "topic": data.topic,
        "level": data.level,
        "questions": [],
        "answers": {},
        "inviteCode": invite_code,
        "status": "waiting"
    }
    return {"challengeId": challenge_id, "inviteCode": invite_code}

@router.post("/challenges/join")
def join_challenge(data: JoinChallenge):
    for cid, ch in challenges.items():
        if ch['inviteCode'] == data.inviteCode:
            if ch['opponent'] is not None:
                raise HTTPException(status_code=400, detail="Challenge already has an opponent.")
            ch['opponent'] = data.userId
            return {"challengeId": cid}
    raise HTTPException(status_code=404, detail="Invite code not found.")

@router.post("/challenges/{challenge_id}/start")
def start_challenge(challenge_id: str):
    challenge = challenges.get(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found.")

    if not challenge['opponent']:
        raise HTTPException(status_code=400, detail="Waiting for opponent to join.")

    # Call to Gemma server
    response = requests.post("http://localhost:5000/generate", json={
        "subject": challenge['subject'],
        "topic": challenge['topic'],
        "level": challenge['level']
    })
    questions = response.json().get("questions", [])
    challenge['questions'] = questions
    challenge['status'] = 'in_progress'
    return {"questions": questions}

@router.post("/challenges/{challenge_id}/answer")
def submit_answer(challenge_id: str, data: AnswerSubmission):
    challenge = challenges.get(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found.")

    if data.userId not in [challenge['creator'], challenge['opponent']]:
        raise HTTPException(status_code=403, detail="Not a participant.")

    user_answers = challenge['answers'].setdefault(data.userId, {})
    user_answers[data.questionIndex] = data.answer
    return {"message": "Answer recorded."}

@router.get("/challenges/{challenge_id}/result")
def get_result(challenge_id: str):
    challenge = challenges.get(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found.")

    questions = challenge['questions']
    scores = {}
    for user in [challenge['creator'], challenge['opponent']]:
        answers = challenge['answers'].get(user, {})
        score = 0
        for idx, q in enumerate(questions):
            if str(answers.get(idx)) == str(q['answer']):
                score += 1
        scores[user] = score

    winner = max(scores, key=scores.get) if scores[challenge['creator']] != scores[challenge['opponent']] else "Draw"
    return {"scores": scores, "winner": winner}
