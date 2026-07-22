from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from app.schemas.user import CamelModel

class ProfileAccessLevel(str, Enum):
    OWNER = "owner"
    FULL_ACCESS = "full_access"
    CARE_PARTNER = "care_partner"
    VIEW_ONLY = "view_only"

class ProfilePermission(str, Enum):
    VIEW_PROFILE = "view_profile"
    ADD_MEDICATION = "add_medication"
    EDIT_MEDICATION = "edit_medication"
    VIEW_QR_CODE = "view_qr_code"
    MANAGE_ACCESS = "manage_access"
    DELETE_PROFILE = "delete_profile"

# Decoupled, centralized permission dictionary mapping roles -> capabilities
ACCESS_LEVEL_PERMISSIONS = {
    ProfileAccessLevel.OWNER: {
        ProfilePermission.VIEW_PROFILE,
        ProfilePermission.ADD_MEDICATION,
        ProfilePermission.EDIT_MEDICATION,
        ProfilePermission.VIEW_QR_CODE,
        ProfilePermission.MANAGE_ACCESS,
        ProfilePermission.DELETE_PROFILE,
    },
    ProfileAccessLevel.FULL_ACCESS: {
        ProfilePermission.VIEW_PROFILE,
        ProfilePermission.ADD_MEDICATION,
        ProfilePermission.EDIT_MEDICATION,
        ProfilePermission.VIEW_QR_CODE,
        ProfilePermission.MANAGE_ACCESS,
        ProfilePermission.DELETE_PROFILE,
    },
    ProfileAccessLevel.CARE_PARTNER: {
        ProfilePermission.VIEW_PROFILE,
        ProfilePermission.ADD_MEDICATION,
        ProfilePermission.EDIT_MEDICATION,
        ProfilePermission.VIEW_QR_CODE,
    },
    ProfileAccessLevel.VIEW_ONLY: {
        ProfilePermission.VIEW_PROFILE,
        ProfilePermission.VIEW_QR_CODE,
    }
}

class ProfileAccessGrantRequest(CamelModel):
    identity: str  # Email or Phone Number
    access_level: ProfileAccessLevel
    relation: str  # E.g. father, friend, patient

class ProfileAccessRevokeRequest(CamelModel):
    user_id: str

class ProfileAccessResponse(CamelModel):
    id: int
    profile_id: int
    user_id: str
    identity: Optional[str] = None  # resolved email or phone
    access_level: str
    relation: str
    granted_by: Optional[str] = None
    created_at: datetime
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None

    class Config:
        from_attributes = True
