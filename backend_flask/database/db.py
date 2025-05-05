import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Global Variables
client = None
db = None
users_collection = None
role_menu_collection = None
models= None

def init_db():
    
    """Initialize MongoDB connection and collections."""
    global client, db, users_collection, role_menu_collection, models

    MONGO_URI = os.getenv("MONGO_URI")
    if not MONGO_URI:
        raise Exception("MongoDB URI not found in environment variables.")

    client = MongoClient(MONGO_URI, tlsAllowInvalidCertificates=True)
    db = client.get_database()
    
    # Initialize collections
    users_collection = db["users"]
    models=db["models"]
    role_menu_collection = db["role_menu"]
    print("✅ MongoDB initialized successfully!")

def close_db():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        print("🛑 MongoDB connection closed.")
