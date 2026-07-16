from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.response import ApiResponse
from app.schemas.user import UserResponse, ProfileUpdate
from app.crud.user import update_profile

router = APIRouter()

@router.post("/health-profile", response_model=ApiResponse[UserResponse])
def save_health_profile_post(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_profile = update_profile(db, user_uid=current_user.uid, profile_update=profile_data)
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
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_profile = update_profile(db, user_uid=current_user.uid, profile_update=profile_data)
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
