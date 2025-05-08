from fastapi import APIRouter, Depends, HTTPException
from app.models.assessment import SelfAssessmentRequest
from app.services.self_assessment import save_assessment, get_assessment

router = APIRouter(prefix="/v2", tags=["Assessment"])

@router.post("/self-assessment")
async def submit_self_assessment(
    request: SelfAssessmentRequest,
    user_id: str  # Assuming you pass this from auth/session
):
    result = await save_assessment(user_id, request)
    return {"message": "Saved", "result": result}

@router.get("/self-assessment")
async def fetch_self_assessment(user_id: str):
    data = await get_assessment(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="No self-assessment data found")
    return {"message": "Fetched", "data": data}
