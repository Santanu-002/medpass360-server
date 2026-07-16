from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.response import ApiResponse
from app.schemas.medical_option import GroupedMedicalOptionsResponse, MedicalOptionResponse
from app.crud import medical_option as medical_option_crud

router = APIRouter()

def map_allergy_option(x) -> MedicalOptionResponse:
    return MedicalOptionResponse(
        uid=x.uid,
        category=f"{x.allergy_type}_allergy",
        slug=x.slug,
        display_name=x.display_name,
        created_by=x.created_by,
        status=x.status
    )

def map_condition_option(x) -> MedicalOptionResponse:
    category = "chronic_condition" if x.condition_type == "chronic" else "syndrome"
    return MedicalOptionResponse(
        uid=x.uid,
        category=category,
        slug=x.slug,
        display_name=x.display_name,
        created_by=x.created_by,
        status=x.status
    )

def map_family_history_option(x) -> MedicalOptionResponse:
    return MedicalOptionResponse(
        uid=x.uid,
        category="family_history",
        slug=x.slug,
        display_name=x.display_name,
        created_by=x.created_by,
        status=x.status
    )

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
    
    response_data = GroupedMedicalOptionsResponse(
        chronic_conditions=[map_condition_option(i) for i in grouped_data["chronic_condition"]],
        syndromes=[map_condition_option(i) for i in grouped_data["syndrome"]],
        drug_allergies=[map_allergy_option(i) for i in grouped_data["drug_allergy"]],
        food_allergies=[map_allergy_option(i) for i in grouped_data["food_allergy"]],
        environmental_allergies=[map_allergy_option(i) for i in grouped_data["environmental_allergy"]],
        family_history=[map_family_history_option(i) for i in grouped_data["family_history"]],
    )
    
    return ApiResponse(
        success=True,
        message="Grouped medical options retrieved successfully.",
        data=response_data
    )

@router.get("/medical-options/allergies", response_model=ApiResponse[List[MedicalOptionResponse]])
def get_allergy_options(
    status: str = Query("active", pattern="^(active|inactive)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data = medical_option_crud.get_allergy_options(db=db, user_uid=current_user.uid, status=status)
    return ApiResponse(
        success=True,
        message="Allergy options retrieved successfully.",
        data=[map_allergy_option(i) for i in data]
    )

@router.get("/medical-options/conditions", response_model=ApiResponse[List[MedicalOptionResponse]])
def get_condition_options(
    status: str = Query("active", pattern="^(active|inactive)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data = medical_option_crud.get_condition_options(db=db, user_uid=current_user.uid, status=status)
    return ApiResponse(
        success=True,
        message="Medical condition options retrieved successfully.",
        data=[map_condition_option(i) for i in data]
    )

@router.get("/medical-options/family-history", response_model=ApiResponse[List[MedicalOptionResponse]])
def get_family_history_options(
    status: str = Query("active", pattern="^(active|inactive)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data = medical_option_crud.get_family_history_options(db=db, user_uid=current_user.uid, status=status)
    return ApiResponse(
        success=True,
        message="Family history options retrieved successfully.",
        data=[map_family_history_option(i) for i in data]
    )
