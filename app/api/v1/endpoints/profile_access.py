import io
import qrcode
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.profile import Profile
from app.models.profile_access import ProfileAccess
from app.schemas.response import ApiResponse
from app.schemas.profile_access import (
    ProfileAccessLevel,
    ProfilePermission,
    ACCESS_LEVEL_PERMISSIONS,
    ProfileAccessGrantRequest,
    ProfileAccessResponse
)
from app.crud.user import get_profile_by_uid, get_user_by_identity, ensure_profile_access

router = APIRouter()

def verify_profile_permission(db: Session, profile_uid: str, user_uid: str, required_permission: ProfilePermission) -> Profile:
    # 1. Fetch Profile
    profile = get_profile_by_uid(db, profile_uid=profile_uid)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found."
        )

    # 2. Check active access record
    access = db.query(ProfileAccess).filter(
        ProfileAccess.profile_id == profile.id,
        ProfileAccess.user_id == user_uid,
        ProfileAccess.revoked_at.is_(None)
    ).first()

    if not access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You do not have permissions for this profile."
        )

    # 3. Check specific permission
    allowed_perms = ACCESS_LEVEL_PERMISSIONS.get(ProfileAccessLevel(access.access_level), set())
    if required_permission not in allowed_perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Action forbidden. Required permission: {required_permission.value}"
        )

    return profile


@router.get("/health-profile/access/{profile_uid}", response_model=ApiResponse[List[ProfileAccessResponse]])
def get_profile_access_list(
    profile_uid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify they can manage access
    profile = verify_profile_permission(db, profile_uid, current_user.uid, ProfilePermission.MANAGE_ACCESS)

    # Query all access permissions (including revoked history)
    access_records = db.query(ProfileAccess).filter(
        ProfileAccess.profile_id == profile.id
    ).order_index = ProfileAccess.created_at.asc()
    
    # Wait, order_by instead of order_index
    access_records = db.query(ProfileAccess).filter(
        ProfileAccess.profile_id == profile.id
    ).order_by(ProfileAccess.created_at.asc()).all()

    result = []
    for record in access_records:
        resp = ProfileAccessResponse.model_validate(record)
        
        # Resolve user email/phone for display identity
        access_user = db.query(User).filter(User.uid == record.user_id).first()
        if access_user:
            resp.identity = access_user.phone_number or access_user.email
            
        result.append(resp)

    return ApiResponse(
        success=True,
        message="Profile access list retrieved successfully.",
        data=result
    )


@router.post("/health-profile/access/{profile_uid}", response_model=ApiResponse[ProfileAccessResponse])
def grant_profile_access(
    profile_uid: str,
    req: ProfileAccessGrantRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify current user can manage access
    profile = verify_profile_permission(db, profile_uid, current_user.uid, ProfilePermission.MANAGE_ACCESS)

    # Find the target user by phone or email
    target_user = get_user_by_identity(db, identity=req.identity.strip())
    if not target_user:
        # Create a placeholder user to allow seamless onboarding later
        if "@" in req.identity:
            target_user = User(email=req.identity.strip())
        else:
            target_user = User(phone_number=req.identity.strip())
        db.add(target_user)
        db.commit()
        db.refresh(target_user)

    if target_user.uid == profile.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot grant access to the profile owner."
        )

    # Create/update access
    access = ensure_profile_access(
        db=db,
        profile_id=profile.id,
        user_id=target_user.uid,
        access_level=req.access_level.value,
        relation=req.relation.strip(),
        granted_by=current_user.uid
    )

    resp = ProfileAccessResponse.model_validate(access)
    resp.identity = target_user.phone_number or target_user.email

    return ApiResponse(
        success=True,
        message=f"Access granted to {resp.identity} successfully.",
        data=resp
    )


@router.post("/health-profile/access/{profile_uid}/revoke", response_model=ApiResponse[ProfileAccessResponse])
def revoke_profile_access(
    profile_uid: str,
    target_user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = get_profile_by_uid(db, profile_uid=profile_uid)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found."
        )

    # 1. Authorize: Current user must be owner/have manage access, OR current user is revoking THEIR OWN access
    is_self_revoking = (current_user.uid == target_user_id)
    if not is_self_revoking:
        verify_profile_permission(db, profile_uid, current_user.uid, ProfilePermission.MANAGE_ACCESS)

    # 2. Check active access record
    access = db.query(ProfileAccess).filter(
        ProfileAccess.profile_id == profile.id,
        ProfileAccess.user_id == target_user_id,
        ProfileAccess.revoked_at.is_(None)
    ).first()

    if not access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active access record not found."
        )

    if access.access_level == ProfileAccessLevel.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke access of the profile owner."
        )

    # Soft revoke: log timestamp and user
    access.revoked_at = datetime.utcnow()
    access.revoked_by = current_user.uid
    db.add(access)
    db.commit()
    db.refresh(access)

    resp = ProfileAccessResponse.model_validate(access)
    access_user = db.query(User).filter(User.uid == target_user_id).first()
    if access_user:
        resp.identity = access_user.phone_number or access_user.email

    return ApiResponse(
        success=True,
        message="Profile access revoked successfully.",
        data=resp
    )


@router.get("/health-profile/qr/{profile_uid}")
def get_profile_qr(
    profile_uid: str,
    db: Session = Depends(get_db)
):
    profile = get_profile_by_uid(db, profile_uid=profile_uid)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found."
        )

    # QR URL pointing to the future website view card (currently mock-pointed to google)
    qr_data = f"https://google.com/health-profile-card/{profile_uid}"

    # Generate QR Code image using Python library
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Write to memory stream and respond as PNG
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return Response(
        content=buf.getvalue(),
        media_type="image/png"
    )
