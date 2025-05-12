# backend_flask/update_leaderboard_names.py

from pymongo import MongoClient

try:
    client = MongoClient("mongodb+srv://info:rZHHtbPyt3idpUBR@aitutor.yime0.mongodb.net/annya?retryWrites=true&w=majority&appName=AITutor")
    db = client["new_Annya"]
    leaderboard_collection = db["leaderboard"]
    new_users_collection = db["users"]
except Exception as e:
    print(f"Error connecting to MongoDB: {str(e)}")
    raise

leaderboard_docs = list(leaderboard_collection.find())
print(f"Found {len(leaderboard_docs)} leaderboard documents")

for doc in leaderboard_docs:
    user_id = doc.get("userId")
    if not user_id:
        print(f"No userId found in leaderboard document: {doc}")
        continue

    user = new_users_collection.find_one({"userId": user_id})
    if not user:
        print(f"No user found in new_users_collection for userId: {user_id}")
        continue

    name = user.get("fullName", "Unknown")
    school = user.get("school", "Not Specified")
    print(f"Updating userId: {user_id}, name: {name}, school: {school}")

    leaderboard_collection.update_one(
        {"userId": user_id},
        {"$set": {"name": name, "school": school}}
    )

print("Leaderboard names and schools updated successfully!")