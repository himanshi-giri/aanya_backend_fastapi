# from pymongo import MongoClient

# client = MongoClient("mongodb+srv://info:rZHHtbPyt3idpUBR@aitutor.yime0.mongodb.net/new_annya?retryWrites=true&w=majority&appName=AITutor")
# db = client["new_Annya"]

# # Insert dummy data into 'progress'
# db.progress.insert_one({
#     "user_id": "test_user",
#     "completed_tasks": 5,
#     "pending_tasks": 3,
#     "streak": 2
# })
# print("✅ Test document inserted into 'progress' collection.")



# from pymongo import MongoClient

# # Connect to MongoDB
# client = MongoClient("mongodb+srv://info:rZHHtbPyt3idpUBR@aitutor.yime0.mongodb.net/new_annya?retryWrites=true&w=majority&appName=AITutor")
# db = client["new_Annya"]

# # Insert document in your desired format
# db.progress.insert_one({
#     "user_id": "test_user",
#     "levelUpProgress": [
#         {"level": 1, "timestamp": "2025-05-15T10:00:00Z"},
#         {"level": 2, "timestamp": "2025-05-16T10:00:00Z"}
#     ],
#     "weeklyStats": [
#         {"week": "2025-W20", "tasksCompleted": 12},
#         {"week": "2025-W21", "tasksCompleted": 8}
#     ],
#     "completedTasks": [
#         {"task_id": "t1", "title": "Intro to Python"},
#         {"task_id": "t2", "title": "Loops"}
#     ],
#     "pendingTasks": [
#         {"task_id": "t3", "title": "Functions"},
#         {"task_id": "t4", "title": "Modules"}
#     ]
# })

# print("✅ Test document inserted into 'progress' collection in desired format.")




# from pymongo import MongoClient

# # Connect to MongoDB
# client = MongoClient("mongodb+srv://info:rZHHtbPyt3idpUBR@aitutor.yime0.mongodb.net/new_annya?retryWrites=true&w=majority&appName=AITutor")
# db = client["new_Annya"]

# # Insert document with full structure for testing
# db.progress.insert_one({
#     "user_id": "test_user",
#     "levelUpProgress": [
#         {
#             "subject": "Quadratic Equation",
#             "progress": 100,
#             "currentLevel": "Developing",
#             "nextLevel": "Proficient"
#         }
#     ],
#     "weeklyStats": [
#         {
#             "title": "Challenge Completed",
#             "value": "12",
#             "period": "This Week",
#             "color": "text-purple-600"
#         }
#     ],
#     "completedTasks": [
#         {
#             "icon": "📊",
#             "text": "You completed 20 practice problems in Coordinate Geometry"
#         }
#     ],
#     "pendingTasks": [
#         {
#             "number": 1,
#             "subject": "Biology",
#             "topic": "Human Anatomy",
#             "lastPracticed": "10 days ago",
#             "progress": 40,
#             "practicesNeeded": "2 more times to get mastery"
#         }
#     ]
# })

# print("✅ Test document inserted into 'progress' collection in expected format.")




from pymongo import MongoClient
from datetime import datetime, timezone
import uuid

# Connect to MongoDB
client = MongoClient("mongodb+srv://info:rZHHtbPyt3idpUBR@aitutor.yime0.mongodb.net/new_annya?retryWrites=true&w=majority&appName=AITutor")
db = client["new_Annya"]

# Create sample challenge document
challenge_data = {
    "challengeId": str(uuid.uuid4()),
    "inviteCode": "XYZ123",
    "creator": "test_user_011",
    "opponent": "test_user1",
    "subject": "Mathematics",
    "topic": "Algebra",
    "level": "Easy",
    "subtopic": "Linear Equations",
    "status": "completed",
    "createdAt": datetime.now(timezone.utc)
}

# Insert into 'challenges' collection
db.challenges.insert_one(challenge_data)

print("✅ Sample challenge inserted into 'challenges' collection.")
