
from re import sub
from database.db import init_db
init_db()
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
import uvicorn


# Load environment variables
load_dotenv()



from database.db import users_collection , models, new_users_collection, leaderboard_collection , uploads_collection, solutions_collection, conversation_collection

from routes.v1 import user_routes, auth_routes, file_routes, api_routes, teach_routes  # v1 routes


  # v1 routes/

from routes.v2 import API_routes,play_with_friend,leaderboard,Doubt_solver, EvaluateAnswers,Auth_routes ,subjects,User_route ,goalpractise # v2 route


is_llm_enabled = os.getenv("LLM_ENABLED") == "True"

SECRET_KEY = "your_secret_key_here"
MONGO_URI= os.getenv("MONGO_URI")
# Initialize FastAPI app
app = FastAPI()
 
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve the "uploads" directory as static files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")



app.include_router(API_routes.router)

app.include_router(user_routes.router)
app.include_router(file_routes.router)

app.include_router(play_with_friend.router)
app.include_router(leaderboard.router)
app.include_router(teach_routes.router) # Himanshi
app.include_router(Doubt_solver.router)
app.include_router(EvaluateAnswers.router)

app.include_router(auth_routes.router)
#Sapp.include_router(leaderboard_route.router)
#app.include_router(auth_routes.router)

app.include_router(Auth_routes.router)
app.include_router(subjects.router)
app.include_router(User_route.router)
app.include_router(goalpractise.router)


origins = [
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5173/",    
    "http://localhost:5173/",
    "http://localhost:5173",
    "https://tutor.eduai.live",
    "https://redesigned-space-system-9795qg6rg7xq2pqwr-5173.app.github.dev/",
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
