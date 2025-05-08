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
