from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from config import Config

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
