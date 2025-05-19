from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from config import Config
###from pymongo import MongoClient
# from flask_bcrypt import Bcrypt
# from config import Config
###Jonny
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
###

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


    def update_pending_tasks(self, topic_name: str, last_practiced: datetime, level: str, practice_needed_for_mastery: int, practice_done: int):
        for task in self.pending_tasks:
            if task.topic_name == topic_name:
                task.last_practiced = last_practiced
                task.level = level
                task.practice_needed_for_mastery = practice_needed_for_mastery
                task.practice_done = practice_done
                break
        else:
            self.pending_tasks.append(TopicProgress(topic_name=topic_name, subject="", last_practiced=last_practiced, level=level, practice_needed_for_mastery=practice_needed_for_mastery, practice_done=practice_done))

    def update_weekly_stats(self, challenges_completed: int, questions_answered: int, daily_streak: int, study_time_minutes: int):
        self.weekly_stats.challenges_completed = challenges_completed
        self.weekly_stats.questions_answered = questions_answered
        self.weekly_stats.daily_streak = daily_streak
        self.weekly_stats.study_time_minutes = study_time_minutes

    def add_completed_task(self, message: str, date: datetime):
        self.completed_tasks.append(CompletedTask(message=message, date=date))

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


### Jonny
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
    
    ###