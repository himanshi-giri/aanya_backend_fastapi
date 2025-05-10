from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from database.db import self_assessment_collection
from helpers.auth_utils import get_current_user  # a function that decodes token

router = APIRouter()

class SelfAssessmentRequest(BaseModel):
    levels: dict

@router.post("/v2/self-assessment")
async def save_self_assessment(data: SelfAssessmentRequest, request: Request, user=Depends(get_current_user)):
    try:
        user_id = user["userId"]

        self_assessment_collection.update_one(
            {"userId": user_id},
            {
                "$set": {
                    "levels": data.levels,
                   
                }
            },
            upsert=True
        )

        return {"message": "Self-assessment saved successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v2/self-assessment")
async def get_self_assessment(user=Depends(get_current_user)):
    try:
        user_id = user["userId"]

        data = self_assessment_collection.find_one({"userId": user_id}, {"_id": 0, "levels": 1})
        return {"levels": data["levels"] if data else {}}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
