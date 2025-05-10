from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, RootModel
from database.db import assessment_collection, leaderboard_collection  
from typing import Dict, Optional
import jwt as pyjwt
from typing import List

router = APIRouter(prefix="/v2", tags=["Leaderboard"])
 
