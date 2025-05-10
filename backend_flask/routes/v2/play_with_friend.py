from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
import google.generativeai as genai
import os  # To access environment variables

router = APIRouter(prefix="/play", tags=["Play With Friend"])

# In-memory data store (simulate database)
challenges = {}

# Configure Gemini API (Make sure to set your API key as an environment variable)
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

# ------------------ Models ------------------

class ChallengeCreate(BaseModel):
    creatorId: str
    subject: str
    topic: str
    level: str
    opponentId: Optional[str] = None  # for direct challenge


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

# ------------------ Question Generation using Gemini API ------------------
def generate_sample_questions(subject: str, topic: str, level: str = "medium") -> List[Dict]:
    """
    Generates a dummy set of quiz questions based on subject and topic.
    """
    if subject == "Mathematics" and topic == "Algebra":
        return [
            {
                "question": "What is the value of x in the equation 3x + 2 = 8?",
                "options": ["1", "2", "3", "4"],
                "answer": "2"
            },
            {
                "question": "Simplify the expression: 5y - 2y + 7y",
                "options": ["9y", "10y", "12y", "14y"],
                "answer": "10y"
            }
        ]
    elif subject == "Science" and topic == "Physics":
        return [
            {
                "question": "Which law states that energy cannot be created or destroyed?",
                "options": ["Newton's First Law", "Newton's Second Law", "Law of Conservation of Energy", "Ohm's Law"],
                "answer": "Law of Conservation of Energy"
            },
            {
                "question": "What is the unit of electric current?",
                "options": ["Volt", "Ohm", "Ampere", "Watt"],
                "answer": "Ampere"
            }
        ]
    else:
        return [
            {"question": f"No dummy questions for {subject} - {topic}"}
        ]

async def generate_questions_from_gemini(subject: str, topic: str, level: str = "medium") -> List[Dict]:
    """
    Generates quiz questions using the Gemini Pro model.
    """
    prompt = f"Generate 1 multiple-choice quiz question about {topic} in {subject} at a {level} difficulty level. " \
             "The question should have 4 options labeled A, B, C, D, and clearly indicate the correct answer."
    try:
        response = model.generate_content(prompt)
        response.resolve()  # Ensure the response is fully available

        if response.text:
            # Parse the Gemini response to extract question, options, and answer
            # This parsing logic might need to be adjusted based on Gemini's output format
            lines = response.text.split('\n')
            question_line = next((line for line in lines if line.strip().startswith("Question:")), None)
            options_lines = [line.strip() for line in lines if line.strip().startswith(('A.', 'B.', 'C.', 'D.'))]
            answer_line = next((line for line in lines if line.strip().startswith("Correct Answer:")), None)

            if question_line and len(options_lines) == 4 and answer_line:
                question = question_line.split("Question:")[1].strip()
                options = [opt.split('.', 1)[1].strip() for opt in options_lines]
                answer = answer_line.split("Correct Answer:")[1].strip()
                return [{"question": question, "options": options, "answer": answer}]
            else:
                print(f"Failed to parse Gemini response: {response.text}")
                return [{"question": f"Failed to generate question for {subject} - {topic}"}]
        else:
            print(f"Gemini API returned an empty response for {subject} - {topic}")
            return [{"question": f"Failed to generate question for {subject} - {topic}"}]

    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return [{"question": f"Error generating question for {subject} - {topic}"}]

# ------------------ Routes ------------------

@router.post("/challenges")
async def create_challenge(data: ChallengeCreate):
    challenge_id = str(uuid.uuid4())
    invite_code = uuid.uuid4().hex[:6].upper() if not data.opponentId else None

    challenge_data = {
        "creator": data.creatorId,
        "opponent": data.opponentId,
        "subject": data.subject,
        "topic": data.topic,
        "level": data.level,
        "questions": [],
        "answers": {},
        "inviteCode": invite_code,
        "status": "ready" if data.opponentId else "waiting"
    }

    challenges[challenge_id] = challenge_data

    return {
        "challengeId": challenge_id,
        "inviteCode": invite_code,
        "status": challenge_data["status"]
    }

@router.post("/challenges/join")
async def join_challenge(data: JoinChallenge):
    for cid, ch in challenges.items():
        if ch['inviteCode'] == data.inviteCode:
            if ch['opponent'] is not None:
                raise HTTPException(status_code=400, detail="Challenge already has an opponent.")
            ch['opponent'] = data.userId
            ch['status'] = "ready"
            return {"challengeId": cid}
    raise HTTPException(status_code=404, detail="Invite code not found.")

@router.post("/challenges/{challenge_id}/start")
async def start_challenge(challenge_id: str):
    challenge = challenges.get(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found.")

    if not challenge['opponent']:
        raise HTTPException(status_code=400, detail="Waiting for opponent to join.")

    if challenge['questions']:  # prevent regenerating
        return {"questions": challenge['questions']}

    # Use Gemini API to generate questions
    questions =  generate_sample_questions(challenge['subject'], challenge['topic'], challenge['level'])
    challenge['questions'] = questions
    challenge['status'] = 'in_progress'
    return {"questions": questions}

@router.post("/challenges/{challenge_id}/answer")
async def submit_answer(challenge_id: str, data: AnswerSubmission):
    challenge = challenges.get(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found.")

    if data.userId not in [challenge['creator'], challenge['opponent']]:
        raise HTTPException(status_code=403, detail="Not a participant.")

    user_answers = challenge['answers'].setdefault(data.userId, {})
    user_answers[data.questionIndex] = data.answer
    return {"message": "Answer recorded."}

@router.get("/challenges/{challenge_id}/result")
async def get_result(challenge_id: str):
    challenge = challenges.get(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found.")

    questions = challenge['questions']
    scores = {}
    creator = challenge.get('creator')
    opponent = challenge.get('opponent')

    if creator:
        answers_creator = challenge['answers'].get(creator, {})
        score_creator = sum(1 for idx, q in enumerate(questions) if str(answers_creator.get(idx)) == str(q['answer']))
        scores[creator] = score_creator

    if opponent:
        answers_opponent = challenge['answers'].get(opponent, {})
        score_opponent = sum(1 for idx, q in enumerate(questions) if str(answers_opponent.get(idx)) == str(q['answer']))
        scores[opponent] = score_opponent

    winner = None
    if creator and opponent and scores.get(creator) is not None and scores.get(opponent) is not None:
        if scores[creator] > scores[opponent]:
            winner = creator
        elif scores[opponent] > scores[creator]:
            winner = opponent
        else:
            winner = "Draw"

    return {"scores": scores, "winner": winner}

@router.get("/challenges/user/{user_id}")
async def get_user_challenges(user_id: str):
    user_challenges = [
        {"id": cid, **ch}
        for cid, ch in challenges.items()
        if ch['creator'] == user_id or ch['opponent'] == user_id
    ]
    return {"challenges": user_challenges}