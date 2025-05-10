from fastapi import APIRouter, HTTPException
from typing import List

router = APIRouter(prefix="/api", tags=["Subjects & Topics"])

# Dummy data
subject_topic_map = {
    "Mathematics": ["Algebra", "Geometry", "Calculus"],
    "Science": ["Physics", "Chemistry", "Biology"],
    "History": ["Ancient", "Medieval", "Modern"]
}

@router.get("/subjects", response_model=List[str])
def get_subjects():
    return list(subject_topic_map.keys())

@router.get("/topics", response_model=List[str])
def get_topics(subject: str):
    if subject not in subject_topic_map:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject_topic_map[subject]
