from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.response import ApiResponse
from app.schemas.user import UserResponse, ProfileUpdate, HealthProfileCardResponse
from app.crud.user import update_profile, get_profile_by_uid

router = APIRouter()

@router.post("/health-profile", response_model=ApiResponse[UserResponse])
def save_health_profile_post(
    profile_req: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_profile = update_profile(db, user_uid=current_user.uid, profile_update=profile_req)
    if not target_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to save health profile."
        )
    db.refresh(current_user)
    user_resp = UserResponse.model_validate(current_user)
    return ApiResponse(
        success=True,
        message="Health profile saved successfully.",
        data=user_resp
    )


@router.put("/health-profile", response_model=ApiResponse[UserResponse])
def save_health_profile_put(
    profile_req: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_profile = update_profile(db, user_uid=current_user.uid, profile_update=profile_req)
    if not target_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to save health profile."
        )
    db.refresh(current_user)
    user_resp = UserResponse.model_validate(current_user)
    return ApiResponse(
        success=True,
        message="Health profile saved successfully.",
        data=user_resp
    )


@router.get("/health-profile-card/{profile_uid}", response_model=ApiResponse[HealthProfileCardResponse])
def get_health_profile_card(
    profile_uid: str,
    db: Session = Depends(get_db)
):
    profile = get_profile_by_uid(db, profile_uid=profile_uid)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found."
        )
    
    active_count = sum(1 for m in profile.medications_rel if not m.is_stopped)
    
    qr_code_value = "https://google.com"
    
    card_data = HealthProfileCardResponse(
        first_name=profile.first_name or "",
        last_name=profile.last_name or "",
        active_medication_count=active_count,
        qr_code_value=qr_code_value
    )
    
    return ApiResponse(
        success=True,
        message="Health profile card retrieved successfully.",
        data=card_data
    )


from pydantic import BaseModel
from typing import Optional
from app.models.profile import Allergy, MedicalCondition, ProfileMedicalSelection, Profile
from app.core.utils import slugify

class AllergyAddRequest(BaseModel):
    profile_uid: str
    display_name: str
    allergy_type: str  # 'drug', 'food', 'environmental'

class ConditionAddRequest(BaseModel):
    profile_uid: str
    display_name: str
    condition_type: str  # 'chronic', 'syndrome'
    duration: Optional[str] = None


@router.post("/health-profile/allergy", response_model=ApiResponse[UserResponse])
def add_allergy(
    req: AllergyAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(Profile.uid == req.profile_uid).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
        
    slug = slugify(req.display_name)
    category_name = f"{req.allergy_type}_allergy"
    
    # Get or create Allergy catalog item
    catalog_item = db.query(Allergy).filter(
        Allergy.slug == slug,
        Allergy.allergy_type == req.allergy_type
    ).first()
    
    if not catalog_item:
        catalog_item = Allergy(
            allergy_type=req.allergy_type,
            slug=slug,
            display_name=req.display_name,
            created_by=current_user.uid,
            status="active"
        )
        db.add(catalog_item)
        db.flush()
        
    # Check if selection already exists
    selection = db.query(ProfileMedicalSelection).filter(
        ProfileMedicalSelection.profile_id == profile.id,
        ProfileMedicalSelection.item_uid == catalog_item.uid,
        ProfileMedicalSelection.category == category_name
    ).first()
    
    if not selection:
        db.add(ProfileMedicalSelection(
            profile_id=profile.id,
            item_uid=catalog_item.uid,
            category=category_name
        ))
        db.commit()
        
    db.refresh(current_user)
    return ApiResponse(
        success=True,
        message="Allergy added successfully.",
        data=UserResponse.model_validate(current_user)
    )


@router.delete("/health-profile/allergy", response_model=ApiResponse[UserResponse])
def remove_allergy(
    profile_uid: str,
    display_name: str,
    allergy_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(Profile.uid == profile_uid).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
        
    slug = slugify(display_name)
    category_name = f"{allergy_type}_allergy"
    
    catalog_item = db.query(Allergy).filter(
        Allergy.slug == slug,
        Allergy.allergy_type == allergy_type
    ).first()
    
    if catalog_item:
        db.query(ProfileMedicalSelection).filter(
            ProfileMedicalSelection.profile_id == profile.id,
            ProfileMedicalSelection.item_uid == catalog_item.uid,
            ProfileMedicalSelection.category == category_name
        ).delete(synchronize_session=False)
        db.commit()
        
    db.refresh(current_user)
    return ApiResponse(
        success=True,
        message="Allergy removed successfully.",
        data=UserResponse.model_validate(current_user)
    )


@router.post("/health-profile/condition", response_model=ApiResponse[UserResponse])
def add_condition(
    req: ConditionAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(Profile.uid == req.profile_uid).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
        
    slug = slugify(req.display_name)
    category_name = "chronic_condition" if req.condition_type == "chronic" else "syndrome"
    
    # Get or create MedicalCondition catalog item
    catalog_item = db.query(MedicalCondition).filter(
        MedicalCondition.slug == slug,
        MedicalCondition.condition_type == req.condition_type
    ).first()
    
    if not catalog_item:
        catalog_item = MedicalCondition(
            condition_type=req.condition_type,
            slug=slug,
            display_name=req.display_name,
            created_by=current_user.uid,
            status="active"
        )
        db.add(catalog_item)
        db.flush()
        
    # Check if selection already exists
    selection = db.query(ProfileMedicalSelection).filter(
        ProfileMedicalSelection.profile_id == profile.id,
        ProfileMedicalSelection.item_uid == catalog_item.uid,
        ProfileMedicalSelection.category == category_name
    ).first()
    
    if not selection:
        db.add(ProfileMedicalSelection(
            profile_id=profile.id,
            item_uid=catalog_item.uid,
            category=category_name,
            duration=req.duration
        ))
    else:
        if req.duration is not None:
            selection.duration = req.duration
            db.add(selection)
            
    db.commit()
    db.refresh(current_user)
    return ApiResponse(
        success=True,
        message="Medical condition added successfully.",
        data=UserResponse.model_validate(current_user)
    )


@router.delete("/health-profile/condition", response_model=ApiResponse[UserResponse])
def remove_condition(
    profile_uid: str,
    display_name: str,
    condition_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(Profile.uid == profile_uid).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
        
    slug = slugify(display_name)
    category_name = "chronic_condition" if condition_type == "chronic" else "syndrome"
    
    catalog_item = db.query(MedicalCondition).filter(
        MedicalCondition.slug == slug,
        MedicalCondition.condition_type == condition_type
    ).first()
    
    if catalog_item:
        db.query(ProfileMedicalSelection).filter(
            ProfileMedicalSelection.profile_id == profile.id,
            ProfileMedicalSelection.item_uid == catalog_item.uid,
            ProfileMedicalSelection.category == category_name
        ).delete(synchronize_session=False)
        db.commit()
        
    db.refresh(current_user)
    return ApiResponse(
        success=True,
        message="Medical condition removed successfully.",
        data=UserResponse.model_validate(current_user)
    )


