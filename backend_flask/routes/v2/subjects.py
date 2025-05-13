from fastapi import APIRouter, HTTPException
from typing import List,Optional
from database.db import class_tenth_collection
from pydantic import BaseModel



router = APIRouter(prefix="/api", tags=["Subjects & Topics"])

# Dummy data
subject_topic_map = {
    "Mathematics": ["Algebra", "Geometry", "Calculus"],
    "Science": ["Physics", "Chemistry", "Biology"],
    "History": ["Ancient", "Medieval", "Modern"]
}

# @router.get("/subjects", response_model=List[str])
# def get_subjects():
    
#     return list(subject_topic_map.keys())

# @router.get("/topics", response_model=List[str])
# def get_topics(subject: str):
#     if subject not in subject_topic_map:
#         raise HTTPException(status_code=404, detail="Subject not found")
#     return subject_topic_map[subject]

# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# from pymongo import MongoClient
# from typing import List, Dict



# Pydantic models
class Subtopic(BaseModel):
    name: str
    level:  Optional[str] = None

class Topic(BaseModel):
    name: str
    level: Optional[str] = None  # allow None for level
    subtopics: List[Subtopic] = []

class Subject(BaseModel):
    name: str
    topics: List[Topic]

@router.get("/subjects")
async def get_subjects():
    try:
        # Fetch subjects from MongoDB
        subjects_data = list(class_tenth_collection.find({}, {"_id": 0}))  # Including topics
       
        if not subjects_data:
            raise HTTPException(status_code=404, detail="No subjects found")

        # Constructing the response with the correct format
        subjects = []
        for document in subjects_data:
            for subject_name in document.keys():
                # Check if the key is a subject name
                if subject_name != "level" and subject_name != "subtopics":  # Exclude non-subject keys
                    subjects.append( subject_name)

        return subjects

    except Exception as e:
        raise HTTPException(status_code=500, detail="Error fetching subjects from database")

# API Endpoint 1: Get topics based on subject
@router.get("/subjects/{subject_name}/topics")
async def get_topics_by_subject(subject_name: str):
    try:
        #print("Requested subject:", subject_name)
        subject_document = class_tenth_collection.find_one({})
        #print("Fetched document keys:", list(subject_document.keys()) if subject_document else None)

        if not subject_document:
            raise HTTPException(status_code=404, detail="Subject data not found")

        subject = subject_document.get(subject_name)
        print(subject)
        if not subject:
            raise HTTPException(status_code=404, detail=f"Subject '{subject_name}' not found")

        topics = []
        for topic_name, topic_details in subject.items():
            subtopics = []
            if 'subtopics' in topic_details:
                for subtopic_name, subtopic_details in topic_details['subtopics'].items():
                    subtopics.append(
                        Subtopic(
                            name=subtopic_name,
                            level=subtopic_details.get('level')
                        )
                    )
            topics.append(
                Topic(
                    name=topic_name,
                    level=topic_details.get('level'),
                    subtopics=subtopics
                )
            )

        return topics

    except HTTPException as http_exc:
        raise http_exc  # Re-raise FastAPI-specific exceptions

    except Exception as e:
        # Log unexpected errors for debugging
        print(f"Unexpected error in get_topics_by_subject: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# API Endpoint 2: Get subtopics based on topic
@router.get("/subjects/{subject_name}/topics/{topic_name}/subtopics", response_model=List[Subtopic])
async def get_subtopics_by_topic(subject_name: str, topic_name: str):
    subject_document = class_tenth_collection.find_one({subject_name: {"$exists": True}})
    
    if not subject_document:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    topic_details = subject_document.get(subject_name, {}).get(topic_name)
    
    if not topic_details or "subtopics" not in topic_details:
        raise HTTPException(status_code=404, detail="Topic or subtopics not found")
    
    subtopics = [
        Subtopic(name=subtopic_name, level=subtopic_details['level'])
        for subtopic_name, subtopic_details in topic_details['subtopics'].items()
    ]
    
    return subtopics

# API Endpoint 3: Get subject, topic, and subtopics details
@router.get("/subjects/{subject_name}/topics/{topic_name}", response_model=Topic)
async def get_topic_details(subject_name: str, topic_name: str):
    subject_document = class_tenth_collection.find_one({subject_name: {"$exists": True}})
    
    if not subject_document:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    topic_details = subject_document.get(subject_name, {}).get(topic_name)
    
    if not topic_details:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    subtopics = [
        Subtopic(name=subtopic_name, level=subtopic_details['level'])
        for subtopic_name, subtopic_details in topic_details.get('subtopics', {}).items()
    ]
    
    topic = Topic(name=topic_name, level=topic_details['level'], subtopics=subtopics)
    
    return topic
