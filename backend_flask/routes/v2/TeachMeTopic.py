from fastapi import APIRouter, Query
import google.generativeai as genai
import requests
import os

router = APIRouter(prefix="/v2", tags=["Auth"])

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

# Load API key from environment variable
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")


@router.get("/youtube-videos")
def get_youtube_videos(
    subject: str = Query(...),
    topic: str = Query(...),
    subtopic: str = Query(None),  # Make subtopic an optional query parameter
):
    query = f"{subject} {topic}"
    if subtopic:  # Add subtopic to the query if provided
        query += f" {subtopic}"
    query += " tutorial"  # Add "tutorial" for more relevant results

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

    # Now get video statistics
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

    # Sort by views and likes combined (simple weight)
    videos.sort(key=lambda x: (x["views"] + 2 * x["likes"]), reverse=True)

    return {"videos": videos[:3]}


@router.get("/gemini-chatResponse")
async def get_chat_response(
    subject: str = Query(...),
    topic: str = Query(...),
    subtopic: str = Query(None),
):
    """
    Generates a chat response using the Gemini API based on the provided subject,
    topic, and optional subtopic.

    Args:
        subject (str): The subject of the query.
        topic (str): The topic of the query.
        subtopic (str, optional): The subtopic of the query. Defaults to None.

    Returns:
        dict: A dictionary containing the generated chat response.  Returns
              {"response": "..."} on success and {"error": "..."} on failure.
    """
    try:
        # Construct the prompt.  Make it more robust.
        prompt = f"Explain {topic} in {subject}."
        if subtopic:
            prompt += f"  Include details about {subtopic}."
        prompt += "  Provide a concise and informative explanation suitable for a student."

        # Generate content
        response = model.generate_content(prompt)

        # Check for a successful response.
        if response and response.text:
            return {"response": response.text}
        else:
            return {"error": "Failed to generate response: No text returned"}

    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}
