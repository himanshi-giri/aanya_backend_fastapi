
# done by himanshi
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List, Optional
import aiohttp
import asyncio
import os
#from utils.gemini_helper import generate_gemini_response

load_dotenv()

router = APIRouter(prefix="/teach", tags=["Teach"])

# Gemini config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Gemini Response Generator
async def generate_gemini_response(prompt: str):
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    async with aiohttp.ClientSession() as session:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with session.post(
                    GEMINI_API_URL,
                    params={"key": GEMINI_API_KEY},
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    data = await response.json()
                    if response.status == 200 and data.get("candidates"):
                        return data["candidates"][0]["content"]["parts"][0]["text"]
                    elif response.status == 429:
                        await asyncio.sleep(RETRY_DELAY * attempt)
                        continue
                    else:
                        raise Exception(data.get("error", {}).get("message", "Unknown Error"))
            except Exception as e:
                if attempt == MAX_RETRIES:
                    raise Exception(f"Gemini API failed after {MAX_RETRIES} retries: {str(e)}")

# Data
subjects_data = [
    {"id": 1, "name": "Mathematics"},
    {"id": 2, "name": "Science"},
    {"id": 3, "name": "History"},
    {"id": 4, "name": "General Knowledge"},
    {"id": 5, "name": "Machine Learning"}
]

topics_by_subject = {
    "Mathematics": [
        "Chapter 1 Real Numbers", "Chapter 2 Polynomials", "Chapter 3 Pair of Linear Equations in Two Variables",
        "Chapter 4 Quadratic Equations", "Chapter 5 Arithematic Progressions", "Chapter 6 Triangles",
        "Chapter 7 Coordinate Geometry", "Chapter 8 Introduction to Trigonometry",
        "Chapter 9 Some Applications of Trigonometry", "Chapter 10 Circles", "Chapter 11 Areas Related to Circles",
        "Chapter 12 Surface Areas and Volumes", "Chapter 13 Statistics", "Chapter 14 Probability"
    ],
    "Science": [
        "Chapter 1 Chemical Reactions and Equations", "Chapter 2 Acids,Bases and Salts",
        "Chapter 3 Metals and Non-Metals", "Chapter 4 Carbon and its Compounds", "Chapter 5 Life Processes",
        "Chapter 6 Control and Coordination", "Chapter 7 How do Organisms Reproduce?", "Chapter 8 Heredity",
        "Chapter 9 Light-Reflection and Refraction", "Chapter 10 The Human Eye and the Colourful World",
        "Chapter 11 Electricity", "Chapter 12 Magnetic Effects of Electric Current", "Chapter 13 Our Environment"
    ],
    "History": [
        "Chapter 1 The Rise of Nationalism in Europe", "Chapter 2 Nationalism in India",
        "Chapter 3 The Making of a Global World", "Chapter 4 The Age of Industrialisation",
        "Chapter 5 Print Culture and the Modern World", "Chapter "
    ],
    "General Knowledge": ["Technology", "Sports"],
    "Machine Learning": ["Supervised Learning", "Unsupervised Learning"]
}

# Pydantic models for request validation
class TeachTopicRequest(BaseModel):
    subject: str
    topic: str

class AnswerQuestionRequest(BaseModel):
    subject: str
    topic: str
    question: str

# Routes
@router.get("/")
def teachHome():
    return {"Message": "Welcome to teach API"}

@router.get("/subjects")
async def subjects():
    return subjects_data

@router.get("/topics/{subject}")
async def topics(subject: str):
    if subject not in topics_by_subject:
        raise HTTPException(status_code=400, detail="Invalid subject")
    return [{"id": idx + 1, "name": topic} for idx, topic in enumerate(topics_by_subject[subject])]

@router.post("/teachtopic")
async def teach_topic_route(request: TeachTopicRequest):
    subject = request.subject
    topic = request.topic

    if not subject or not topic:
        raise HTTPException(status_code=400, detail="Subject and topic are required")

    prompt1 = f"""
You are Aanya, an expert AI tutor specialized in teaching {subject}.
Please provide a comprehensive lesson on {topic} within {subject}. Your response should be tailored for a student in middle or high school.

Structure your response with the following sections:
1. Introduction: Brief overview of what {topic} is and why it's important in {subject}
2. Key Concepts: The fundamental ideas and definitions in {topic}
3. Detailed Explanation: In-depth discussion with examples and illustrations
4. Applications: How {topic} is used in real-world scenarios
5. Practice Problems: 2-3 questions with solutions to test understanding
6. Summary: Recap of key points learned

After and before each section/heading add a horizontal bar that divides each section well.
Format your response in HTML for better readability with appropriate headings, paragraphs, lists, and emphasis.
The content should be similar in alignments and spacing as in any real life textbook.
"""

    content = await generate_gemini_response(prompt1)
    return {"subject": subject, "topic": topic, "content": content}

@router.post("/question")
async def answer_question_route(request: AnswerQuestionRequest):
    subject = request.subject
    topic = request.topic
    question = request.question

    if not subject or not topic or not question:
        raise HTTPException(status_code=400, detail="Subject, topic, and question are required")

    prompt2 = f"""
As Aanya, an expert AI tutor specializing in {subject}, please answer the following question about {topic}:

"{question}"

Provide a clear and concise answer using plain text only. Structure your response with:
1. A direct answer to the question
2. A simple explanation with key points
3. If relevant, 1-2 examples or analogies to illustrate the concept

Keep your response conversational, friendly, and suitable for a Class 10 student reading from a NCERT textbook. Do not use any formatting symbols like asterisks, bullet points, or Markdown. Use plain line breaks and paragraphs instead.
"""

    answer = await generate_gemini_response(prompt2)
    return {"question": question, "answer": answer}
