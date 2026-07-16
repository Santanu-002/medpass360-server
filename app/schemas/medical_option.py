from typing import Optional, List
from app.schemas.user import CamelModel

class MedicalOptionResponse(CamelModel):
    uid: str
    category: str
    slug: str
    display_name: str
    created_by: Optional[str] = None
    status: str

    class Config:
        from_attributes = True

class GroupedMedicalOptionsResponse(CamelModel):
    chronic_conditions: List[MedicalOptionResponse]
    syndromes: List[MedicalOptionResponse]
    drug_allergies: List[MedicalOptionResponse]
    food_allergies: List[MedicalOptionResponse]
    environmental_allergies: List[MedicalOptionResponse]
    family_history: List[MedicalOptionResponse]
