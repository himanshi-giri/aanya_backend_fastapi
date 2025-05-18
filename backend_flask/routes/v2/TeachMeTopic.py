from fastapi import APIRouter, Query
import requests
import os

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

router = APIRouter(prefix="/v2", tags=["Auth"])

@router.get("/youtube-videos")
def get_youtube_videos(subject: str = Query(...), topic: str = Query(...)):
    query = f"{subject} {topic} tutorial"
    url = "https://www.googleapis.com/youtube/v3/search"

    search_params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": 5,
        "key": YOUTUBE_API_KEY
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
        "key": YOUTUBE_API_KEY
    }

    details_response = requests.get(details_url, params=details_params)
    video_details = details_response.json()

    videos = []
    for item in video_details.get("items", []):
        videos.append({
            "videoId": item["id"],
            "title": item["snippet"]["title"],
            "views": int(item["statistics"].get("viewCount", 0)),
            "likes": int(item["statistics"].get("likeCount", 0))
        })

    # Sort by views and likes combined (simple weight)
    videos.sort(key=lambda x: (x["views"] + 2 * x["likes"]), reverse=True)

    return {"videos": videos[:3]}