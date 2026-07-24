from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.profile import Profile
from app.schemas.response import ApiResponse
from app.schemas.profile_share import ProfileShareCreate, ProfileShareResponse
from app.schemas.user import ProfileResponse
from app.schemas.profile_access import ProfilePermission
from app.api.v1.endpoints.profile_access import verify_profile_permission
from app.crud.profile_share import (
    create_profile_share,
    get_active_profile_share,
    get_profile_share_by_token,
    revoke_profile_share
)

router = APIRouter()

@router.post("/health-profile/qr/{profile_uid}/temp", response_model=ApiResponse[ProfileShareResponse])
def generate_temp_qr(
    profile_uid: str,
    req: ProfileShareCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify user has permission to view/manage QR code
    profile = verify_profile_permission(
        db=db,
        profile_uid=profile_uid,
        user_uid=current_user.uid,
        required_permission=ProfilePermission.VIEW_QR_CODE
    )
    
    share = create_profile_share(
        db=db,
        profile_id=profile.id,
        created_by=current_user.uid,
        max_uses=req.max_uses,
        expires_in_days=req.expires_in_days
    )
    
    return ApiResponse(
        success=True,
        message="Temporary QR code generated successfully.",
        data=ProfileShareResponse.model_validate(share)
    )

@router.get("/health-profile/qr/{profile_uid}/temp", response_model=ApiResponse[Optional[ProfileShareResponse]])
def get_active_temp_qr(
    profile_uid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = verify_profile_permission(
        db=db,
        profile_uid=profile_uid,
        user_uid=current_user.uid,
        required_permission=ProfilePermission.VIEW_QR_CODE
    )
    
    share = get_active_profile_share(db=db, profile_id=profile.id)
    
    if not share:
        return ApiResponse(
            success=True,
            message="No active temporary QR code found.",
            data=None
        )
        
    return ApiResponse(
        success=True,
        message="Active temporary QR code retrieved successfully.",
        data=ProfileShareResponse.model_validate(share)
    )

@router.delete("/health-profile/qr/{profile_uid}/temp/{token}", response_model=ApiResponse)
def delete_temp_qr(
    profile_uid: str,
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Deletion is a management action, verify MANAGE_ACCESS permission
    verify_profile_permission(
        db=db,
        profile_uid=profile_uid,
        user_uid=current_user.uid,
        required_permission=ProfilePermission.MANAGE_ACCESS
    )
    
    revoke_profile_share(db=db, token=token)
    
    return ApiResponse(
        success=True,
        message="Temporary QR code revoked successfully."
    )

@router.get("/health-profile/share/{token}", response_model=ApiResponse[ProfileResponse])
def get_shared_profile(
    token: str,
    db: Session = Depends(get_db)
):
    share = get_profile_share_by_token(db=db, token=token)
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid sharing code."
        )
        
    if not share.is_active or share.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This sharing code has expired or been revoked."
        )
        
    if share.max_uses is not None and share.uses_count >= share.max_uses:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This sharing code has reached its maximum usage limit."
        )
        
    # Increment usage count
    share.uses_count += 1
    db.add(share)
    db.commit()
    db.refresh(share)
    
    return ApiResponse(
        success=True,
        message="Shared profile retrieved successfully.",
        data=ProfileResponse.model_validate(share.profile)
    )
