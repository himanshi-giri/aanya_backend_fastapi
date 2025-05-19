import os
from pymongo import MongoClient
from gridfs import GridFS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Global Variables
client = None
db = None
annya_db = None
new_annya_db = None


assessment_collection=None
create_goal=None
class_tenth_collection=None

users_collection = None
role_menu_collection = None
models = None
leaderboard_collection = None
new_users_collection = None
assessment_collection = None
Doubt_solver = None
uploads_collection = None
solutions_collection = None
conversation_collection = None
fs= None
challenges_collection=None
progress_collection = None

def init_db():
    """Initialize MongoDB connection and collections."""

    global client, db, users_collection, role_menu_collection, models
    global new_users_collection, leaderboard_collection, assessment_collection,challenges_collection
    global Doubt_solver, uploads_collection, solutions_collection, conversation_collection,create_goal,class_tenth_collection
    global annya_db, new_annya_db
    global progress_collection

    MONGO_URI = os.getenv("MONGO_URI")
    if not MONGO_URI:
        raise Exception("MongoDB URI not found in environment variables.")

    client = MongoClient(MONGO_URI, tlsAllowInvalidCertificates=True)
    db = client.get_database()
    annya_db = client["annya"]
    new_annya_db = client["new_Annya"]

    # Initialize collections
    users_collection = annya_db["users"]
    models = annya_db["models"]
    role_menu_collection = annya_db["role_menu"]

    new_users_collection = new_annya_db["users"]
    leaderboard_collection = new_annya_db["leaderboard"]
    assessment_collection = new_annya_db["self_assessments"]
    uploads_collection = new_annya_db["uploads"]
    solutions_collection = new_annya_db["solutions"]
    conversation_collection = new_annya_db["conversation"]
    challenges_collection = new_annya_db["challenges"]
    progress_collection = new_annya_db["progress"]

    db.fs = GridFS(new_annya_db)

   
    create_goal = new_annya_db["create_goal"]

    class_tenth_collection = new_annya_db["class_tenth"]

    
    print("✅ MongoDB initialized successfully!")

def close_db():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        print("🛑 MongoDB connection closed.")
