from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from config import Config
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Initialize MongoDB connection
client = MongoClient(Config.MONGO_URI)
db = client.get_database("annya")  # Change to your database name
users_collection = db["users"]

# Initialize Bcrypt for password hashing
bcrypt = Bcrypt()

def find_user(email):
    """Find a user by email in MongoDB."""
    return users_collection.find_one({"email": email})

def create_user(email, password):
    """Create a new user in MongoDB with a hashed password."""
    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
    users_collection.insert_one({"email": email, "password": hashed_password})


class TopicProgress(BaseModel):
    topic_name: str
    subject: str
    last_practiced: datetime
    level: str
    practice_needed_for_mastery: int
    practice_done: int

class CompletedTask(BaseModel):
    message: str
    date: datetime

class WeeklyStats(BaseModel):
    challenges_completed: int
    questions_answered: int
    daily_streak: int
    study_time_minutes: int  # store as minutes, convert on frontend

class UserProgress(BaseModel):
    email: str
    levels: dict  # e.g., {"Quadratic Equation": "Proficient"}
    completed_tasks: List[CompletedTask]
    pending_tasks: List[TopicProgress]
    weekly_stats: WeeklyStats
