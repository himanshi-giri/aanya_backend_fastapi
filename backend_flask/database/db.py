import os
from pymongo import MongoClient
from dotenv import load_dotenv
from gridfs import GridFS

# Load environment variables
load_dotenv()

# MongoDB Global Variables
client = None
db = None
annya_db = None
new_annya_db = None
new_users_collection = None
assessment_collection = None
create_goal = None
uploads_collection = None
solutions_collection = None
conversation_collection = None
fs = None
users_collections_collection = None
role_menu_collection = None
models = None
leaderboard_collection = None
new_users_collection = None

def init_db():
    """Initialize MongoDB connection and collections."""
    
    global client, db, users_collection, role_menu_collection, models, new_users_collection, leaderboard_collection, uploads_collection, solutions_collection, conversation_collection
    global annya_db, new_annya_db, assessment_collection, create_goal
    
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
    
    # NEW DB
    new_users_collection = new_annya_db["users"]
    leaderboard_collection = new_annya_db["leaderboard"]
    assessment_collection = new_annya_db["self_assessments"]
    create_goal = new_annya_db["create_goal"]
    uploads_collection = new_annya_db["uploads"]
    solutions_collection = new_annya_db["solutions"]
    conversation_collection = new_annya_db["conversation"]
    
    db.fs = GridFS(new_annya_db)
    
    print("✅ MongoDB initialized successfully!")

def close_db():
    """Close MongoDB connection."""
    
    global client
    if client:
        client.close()
        print("🛑 MongoDB connection closed.")
