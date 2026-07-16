from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.response import ApiResponse
from app.schemas.medical_option import GroupedMedicalOptionsResponse, MedicalOptionResponse
from app.crud import medical_option as medical_option_crud

router = APIRouter()

@router.get("/medical-options", response_model=ApiResponse[GroupedMedicalOptionsResponse])
def get_medical_options(
    status: str = Query("active", pattern="^(active|inactive)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    grouped_data = medical_option_crud.get_grouped_medical_options(
        db=db,
        user_uid=current_user.uid,
        status=status
    )
    
    # Map model instances to Pydantic responses
    response_data = GroupedMedicalOptionsResponse(
        chronic_conditions=[MedicalOptionResponse.model_validate(i) for i in grouped_data["chronic_condition"]],
        syndromes=[MedicalOptionResponse.model_validate(i) for i in grouped_data["syndrome"]],
        drug_allergies=[MedicalOptionResponse.model_validate(i) for i in grouped_data["drug_allergy"]],
        food_allergies=[MedicalOptionResponse.model_validate(i) for i in grouped_data["food_allergy"]],
        environmental_allergies=[MedicalOptionResponse.model_validate(i) for i in grouped_data["environmental_allergy"]],
        family_history=[MedicalOptionResponse.model_validate(i) for i in grouped_data["family_history"]],
    )
    
    return ApiResponse(
        success=True,
        message="Grouped medical options retrieved successfully.",
        data=response_data
    )
