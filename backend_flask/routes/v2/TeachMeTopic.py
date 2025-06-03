import google.generativeai as genai
import requests
import os
import json
from fastapi import APIRouter, Query, HTTPException, Body
from pydantic import BaseModel # Import BaseModel for request body
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled # Import transcript API

router = APIRouter(prefix="/v2", tags=["Auth"])

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Store chat sessions, keyed by a session ID (e.g., videoId for video chat, or a unique ID for topic chat)
# For video chat, we'll store the chat history and perhaps the processed transcript.
active_chat_sessions = {}

# --- Request Body Models ---
class VideoChatRequest(BaseModel):
    video_id: str
    user_query: str

class TopicChatRequest(BaseModel):
    board: str
    grade: str
    subject: str
    topic: str
    subtopic: str = None
    current_stage: str
    student_response: str


@router.get("/youtube-videos")
def get_youtube_videos(
    subject: str = Query(...),
    topic: str = Query(...),
    subtopic: str = Query(None),
):
    query = f"{subject} {topic}"
    if subtopic:
        query += f" {subtopic}"
    query += " tutorial"

    url = "https://www.googleapis.com/youtube/v3/search"

    search_params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": 5,
        "key": YOUTUBE_API_KEY,
    }

    search_response = requests.get(url, params=search_params)
    search_results = search_response.json()

    video_ids = [item["id"]["videoId"] for item in search_results.get("items", [])]

    if not video_ids:
        return {"videos": []}

    details_url = "https://www.googleapis.com/youtube/v3/videos"
    details_params = {
        "part": "snippet,statistics",
        "id": ",".join(video_ids),
        "key": YOUTUBE_API_KEY,
    }

    details_response = requests.get(details_url, params=details_params)
    video_details = details_response.json()

    videos = []
    for item in video_details.get("items", []):
        videos.append(
            {
                "videoId": item["id"],
                "title": item["snippet"]["title"],
                "views": int(item["statistics"].get("viewCount", 0)),
                "likes": int(item["statistics"].get("likeCount", 0)),
            }
        )

    videos.sort(key=lambda x: (x["views"] + 2 * x["likes"]), reverse=True)

    return {"videos": videos[:3]}


@router.get("/gemini-chatResponse")
async def get_chat_response(
    subject: str = Query(...),
    topic: str = Query(...),
    subtopic: str = Query(None),
    stage: str = Query("objectives"),
    user_input: str = Query(None)
):
    try:
        if stage == "objectives":
            key_points = []
            if topic == "Quadratic Equations":
                key_points = [
                    "What a quadratic equation is.",
                    "Different methods to solve quadratic equations (factorization, completing the square, quadratic formula).",
                    "The nature of roots."
                ]
            
            response_text = f"Great choice! By the end of this session, you will understand the basics of **{topic}**, including:"
            for point in key_points:
                response_text += f"\n* {point}"
            response_text += "\nShould we get started or is there something else you would like to add to the learning objectives?"
            
            return {"response": response_text, "next_stage": "overview"}

        elif stage == "overview":
            prompt = f"First, let's talk about what {topic} is and why it is important in {subject}. Provide a brief overview and explain the relevance to real-world applications with a very interesting question or example. Format this with a main heading and bullet points for key aspects. Do not use markdown for links, just regular text. Ask 'Does that make sense?' at the end."
            if subtopic:
                prompt = f"First, let's talk about what {topic} and specifically {subtopic} is and why it is important in {subject}. Provide a brief overview and explain the relevance to real-world applications with a very interesting question or example. Format this with a main heading and bullet points for key aspects. Do not use markdown for links, just regular text. Ask 'Does that make sense?' at the end."
            
            gemini_response = model.generate_content(prompt)
            if gemini_response and gemini_response.text:
                return {"response": gemini_response.text, "next_stage": "key_concepts"}
            else:
                raise HTTPException(status_code=500, detail="Failed to generate overview response: No text returned")
        
        elif stage == "key_concepts":
            prompt = f"Now, let's dive into the key concepts of {topic} in {subject}."
            if subtopic:
                prompt += f" Focus on {subtopic}."
            prompt += " Explain the key concepts clearly, using simple language and examples. Use clear headings for each concept and bullet points for details. Ask 'Do you have any questions about this part?' at the end."
            
            gemini_response = model.generate_content(prompt)
            if gemini_response and gemini_response.text:
                return {"response": gemini_response.text, "next_stage": "practice"}
            else:
                raise HTTPException(status_code=500, detail="Failed to generate key concepts response: No text returned")

        elif stage == "practice":
            prompt = f"Let's work through some examples together for {topic} in {subject}."
            if subtopic:
                prompt += f" focusing on {subtopic}."
            prompt += " Provide a practical example related to the topic and walk the student through the steps. Then, give a similar example for the student to solve on their own. Ask 'Let me know when you're ready to discuss it.' at the end."
            
            gemini_response = model.generate_content(prompt)
            if gemini_response and gemini_response.text:
                return {"response": gemini_response.text, "next_stage": "activity"}
            else:
                raise HTTPException(status_code=500, detail="Failed to generate practice response: No text returned")
        
        elif stage == "activity":
            prompt = f"Let's engage in a quick activity to reinforce your understanding of {topic} in {subject}."
            if subtopic:
                prompt += f" focusing on {subtopic}."
            prompt += " Create a short quiz (2-3 multiple choice questions) or a Q&A session related to the topic. Provide the questions and ask 'How did you find that?' at the end."
            
            gemini_response = model.generate_content(prompt)
            if gemini_response and gemini_response.text:
                return {"response": gemini_response.text, "next_stage": "summary"}
            else:
                raise HTTPException(status_code=500, detail="Failed to generate activity response: No text returned")
        
        elif stage == "summary":
            prompt = f"Let's summarize what we've learned today about {topic} in {subject}."
            if subtopic:
                prompt += f" and {subtopic}."
            prompt += " Recap the main points covered in the session using bullet points. Ask 'Do you have any questions about what we've covered?' at the end."
            
            gemini_response = model.generate_content(prompt)
            if gemini_response and gemini_response.text:
                return {"response": gemini_response.text, "next_stage": "feedback"}
            else:
                raise HTTPException(status_code=500, detail="Failed to generate summary response: No text returned")
        
        elif stage == "feedback":
            feedback_text = "You did a great job today! You actively participated and showed a good understanding of the concepts. Keep practicing to master them!"
            
            resource_prompt = f"Suggest some additional resources (websites, books, channels) to learn more about {topic} in {subject}."
            resource_response = model.generate_content(resource_prompt)
            additional_resources = ""
            if resource_response and resource_response.text:
                additional_resources = resource_response.text

            final_response = f"{feedback_text}\n\nIf you'd like to learn more about {topic}, here are some additional resources:\n{additional_resources}\n\nThank you for learning with me today! I hope you found this session helpful."
            
            return {"response": final_response, "next_stage": "completed"}

        else:
            raise HTTPException(status_code=400, detail="Invalid learning stage provided.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@router.post("/process-student-response")
async def process_student_response(request: TopicChatRequest):
    next_stage_map = {
        "objectives": "overview",
        "overview": "key_concepts",
        "key_concepts": "practice",
        "practice": "activity",
        "activity": "summary",
        "summary": "feedback",
        "feedback": "completed"
    }

    new_stage = next_stage_map.get(request.current_stage, "objectives")

    response_data = await get_chat_response(
        subject=request.subject,
        topic=request.topic,
        subtopic=request.subtopic,
        stage=new_stage,
        user_input=request.student_response
    )
    return response_data

# --- NEW ENDPOINTS FOR VIDEO INTERACTION ---




