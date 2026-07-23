from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.config import settings
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
    request: Request,
    db: Session = Depends(get_db)
):
    profile = get_profile_by_uid(db, profile_uid=profile_uid)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found."
        )
    
    active_count = sum(1 for m in profile.medications_rel if not m.is_stopped)
    
    qr_code_url = f"{str(request.base_url).rstrip('/')}{settings.API_V1_STR}/health-profile/qr/{profile_uid}"
    
    card_data = HealthProfileCardResponse(
        first_name=profile.first_name or "",
        last_name=profile.last_name or "",
        active_medication_count=active_count,
        qr_code_url=qr_code_url
    )
    
    return ApiResponse(
        success=True,
        message="Health profile card retrieved successfully.",
        data=card_data
    )

