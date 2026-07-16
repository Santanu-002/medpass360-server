from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.response import ApiResponse
from app.schemas.user import UserResponse, ProfileUpdate, RegisterRequest
from app.crud.user import update_profile, create_profile
from app.services import registration as registration_service

router = APIRouter()

@router.post("/register", response_model=ApiResponse[UserResponse])
async def register_user(
    request: RegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    updated_user = await registration_service.register_user_profile(
        db=db,
        current_user=current_user,
        first_name=request.first_name,
        last_name=request.last_name,
        gender=request.gender,
        date_of_birth_str=str(request.date_of_birth),
        avatar_url=request.avatar,
        phone_number=request.phone_number,
        email=request.email
    )
    user_resp = UserResponse.model_validate(updated_user)
    return ApiResponse(
        success=True,
        message="Registration completed successfully.",
        data=user_resp
    )

@router.get("/profile", response_model=ApiResponse[UserResponse])
def get_profile(
    current_user: User = Depends(get_current_user)
):
    user_resp = UserResponse.model_validate(current_user)
    return ApiResponse(
        success=True,
        message="Profile retrieved successfully.",
        data=user_resp
    )

@router.put("/profile", response_model=ApiResponse[UserResponse])
def update_user_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    update_profile(db, user_uid=current_user.uid, profile_update=profile_data)
    db.refresh(current_user)
    user_resp = UserResponse.model_validate(current_user)
    return ApiResponse(
        success=True,
        message="Profile updated successfully.",
        data=user_resp
    )
