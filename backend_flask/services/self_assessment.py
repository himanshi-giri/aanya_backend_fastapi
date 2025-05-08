from app.database import assessment_collection
from app.models.assessment import SelfAssessmentRequest
from typing import Any, Dict
from bson import ObjectId

async def save_assessment(user_id: str, data: SelfAssessmentRequest) -> Dict[str, Any]:
    result = await assessment_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "data": data.dict(by_alias=True),
            "system_prompt": "Self-assessment submission"
        }},
        upsert=True
    )
    return {"status": "saved", "modified_count": result.modified_count}

async def get_assessment(user_id: str) -> Dict[str, Any]:
    result = await assessment_collection.find_one({"user_id": user_id})
    if result:
        return result.get("data")
    return {}
