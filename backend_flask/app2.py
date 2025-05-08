
from database.db import init_db
init_db()
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
import uvicorn


# Load environment variables
load_dotenv()



from database.db import users_collection , models, new_users_collection, leaderboard_collection
from routes.v1 import user_routes, auth_routes, file_routes, api_routes, teach_routes  # v1 routes
from routes.v2 import API_routes,play_with_friend,leaderboard,Doubt_solver,auth  # v2 route


is_llm_enabled = os.getenv("LLM_ENABLED") == "True"

SECRET_KEY = os.getenv("SECRET_KEY")
MONGODB_URI: str = os.getenv("MONGODB_URI", "")
# Initialize FastAPI app
app = FastAPI()
 
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve the "uploads" directory as static files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(user_routes.router)
app.include_router(auth_routes.router)
app.include_router(file_routes.router)
app.include_router(API_routes.router)
app.include_router(play_with_friend.router)
app.include_router(leaderboard.router)
app.include_router(teach_routes.router) # Himanshi
app.include_router(Doubt_solver.router)

app.include_router(auth.router)
origins = [
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5173/",    
    "http://localhost:5173/",
     "http://localhost:5173",
    "https://tutor.eduai.live",
     "*"
    # Add other origins if needed
]
# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Home Route
@app.get("/")
async def home():
    return {"message": "FastAPI is running!"}



# Start FastAPI Server (Run with: `uvicorn filename:app --reload`)
if __name__ == "__main__":
    uvicorn.run("app2:app", port=5000, reload=True)
