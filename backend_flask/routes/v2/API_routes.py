from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any

router = APIRouter(prefix="/v2", tags=["API"])

# Define Pydantic models for request body validation
class SubjectLevels(BaseModel):
    """
    Pydantic model to represent the nested structure of subject levels.
    """
    number_system: str = Field(alias="Number System")
    algebra: str = Field(alias="Algebra")
    coordinate_geometry: str = Field(alias="Coordinate Geometry")
    geometry: str = Field(alias="Geometry")
    trigonometry: str = Field(alias="Trigonometry")
    mensuration: str = Field(alias="Mensuration")
    statistics_and_probability: str = Field(alias="Statistics and Probability")

class PhysicsLevels(BaseModel):
    mechanics: str = Field(alias="Mechanics")
    thermodynamics: str = Field(alias="Thermodynamics")
    optics: str = Field(alias="Optics")
    electromagnetism: str = Field(alias="Electromagnetism")

class ChemistryLevels(BaseModel):
    organic_chemistry: str = Field(alias="Organic Chemistry")
    inorganic_chemistry: str = Field(alias="Inorganic Chemistry")
    physical_chemistry: str = Field(alias="Physical Chemistry")
    analytical_chemistry: str = Field(alias="Analytical Chemistry")

class BiologyLevels(BaseModel):
    cell_biology: str = Field(alias="Cell Biology")
    genetics: str = Field(alias="Genetics")
    ecology: str = Field(alias="Ecology")
    human_physiology: str = Field(alias="Human Physiology")
    

class SelfAssessmentRequest(BaseModel):
    """
    Pydantic model to represent the expected request body.  Uses aliases
    to handle the spaces in the keys like 'Number System'.
    """
    mathematics: SubjectLevels = Field(alias="Mathematics")
    physics: PhysicsLevels = Field(alias="Physics")
    chemistry: ChemistryLevels = Field(alias="Chemistry")
    biology: BiologyLevels = Field(alias="Biology")


@ router.get("/check")
async def checked():
    return "my name is vinay"


@router.post("/self-assessment")
async def self_assessment_response(
    request_data: SelfAssessmentRequest, # Use the Pydantic model
) -> Dict[str, Any]:
    """
    Endpoint to receive and process self-assessment data.

    Args:
        request_data (SelfAssessmentRequest): The self-assessment data sent from the frontend.

    Returns:
        dict: A response indicating the data was received and processed.
              The response includes the received data.
    """
    try:
        # Access the data through the validated model
        mathematics_data = request_data.mathematics
        physics_data = request_data.physics
        chemistry_data = request_data.chemistry
        biology_data = request_data.biology
        
        # Process the data as needed.  For example, you could
        # store it in a database, perform calculations, etc.
        # Here, we just log it.
        print("Received self-assessment data:")
        print("Mathematics:", mathematics_data)
        print("Physics:", physics_data)
        print("Chemistry:", chemistry_data)
        print("Biology:", biology_data)

        # Construct a response.  You might want to return a success/fail
        # message, or perhaps some calculated results.
        response_data = {
            "message": "Self-assessment data received successfully",
            "data": {
                "Mathematics": mathematics_data.dict(by_alias=True),
                "Physics": physics_data.dict(by_alias=True),
                "Chemistry": chemistry_data.dict(by_alias=True),
                "Biology": biology_data.dict(by_alias=True),
            }
        }
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
