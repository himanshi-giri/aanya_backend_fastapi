# backend_flask/migrate_leaderboard.py

from pymongo import MongoClient
from datetime import datetime
from dateutil import parser

# Initialize MongoDB client
try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["aanya_db"]  # Replace with your database name
    leaderboard_collection = db["leaderboard"]
    new_users_collection = db["users"]
except Exception as e:
    print(f"Error connecting to MongoDB: {str(e)}")
    raise

# Fetch all existing documents
try:
    all_logs = list(leaderboard_collection.find())
    print(f"Found {len(all_logs)} documents in leaderboard_collection")
except Exception as e:
    print(f"Error fetching documents: {str(e)}")
    raise

# Group by userId
user_logs = {}
for log in all_logs:
    user_id = log.get("userId")
    if not user_id:
        continue  # Skip invalid documents

    # Fetch user from new_users_collection to get the correct name
    user = new_users_collection.find_one({"userId": user_id})
    user_name = user.get("fullName", "Unknown") if user else "Unknown"
    school = user.get("school", "Not Specified") if user else "Not Specified"

    if user_id not in user_logs:
        user_logs[user_id] = {
            "userId": user_id,
            "name": user_name,  # Use the fetched fullName
            "school": school,
            "improvements": [],
            "totalImprovements": 0,
            "lastUpdated": datetime.min
        }

    # If the document is in the old format (has subject, topic, etc. at the root)
    if "subject" in log:
        # Parse the timestamp string to a datetime object
        timestamp_str = log.get("timestamp")
        if isinstance(timestamp_str, str):
            timestamp = parser.isoparse(timestamp_str)
        else:
            timestamp = timestamp_str or datetime.utcnow()

        improvement = {
            "subject": log.get("subject"),
            "topic": log.get("topic"),
            "subtopic": log.get("subtopic"),
            "previous_level": log.get("previous_level"),
            "new_level": log.get("new_level"),
            "timestamp": timestamp
        }
        user_logs[user_id]["improvements"].append(improvement)
        user_logs[user_id]["totalImprovements"] += 1
        if timestamp > user_logs[user_id]["lastUpdated"]:
            user_logs[user_id]["lastUpdated"] = timestamp
    # If the document is in the new format (has improvements array)
    elif "improvements" in log:
        for improvement in log["improvements"]:
            timestamp = improvement.get("timestamp")
            if isinstance(timestamp, str):
                improvement["timestamp"] = parser.isoparse(timestamp)
            user_logs[user_id]["improvements"].append(improvement)
        user_logs[user_id]["totalImprovements"] = log.get("totalImprovements", len(log["improvements"]))
        user_logs[user_id]["lastUpdated"] = log.get("lastUpdated", datetime.min)

# Clear the existing collection
leaderboard_collection.delete_many({})

# Insert the consolidated documents
for user_data in user_logs.values():
    leaderboard_collection.insert_one(user_data)

print("Migration completed successfully!")