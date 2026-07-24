from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models.profile_share import ProfileShare

def deactivate_all_profile_shares(db: Session, profile_id: int) -> None:
    db.query(ProfileShare).filter(
        ProfileShare.profile_id == profile_id,
        ProfileShare.is_active == True
    ).update({"is_active": False, "updated_at": datetime.utcnow()})
    db.commit()

def create_profile_share(
    db: Session,
    profile_id: int,
    created_by: str,
    max_uses: Optional[int] = None,
    expires_in_days: int = 7
) -> ProfileShare:
    # Deactivate any existing active shares first so there's only one active temp QR code
    deactivate_all_profile_shares(db, profile_id)
    
    expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    share = ProfileShare(
        profile_id=profile_id,
        created_by=created_by,
        expires_at=expires_at,
        max_uses=max_uses,
        is_active=True
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return share

def get_active_profile_share(db: Session, profile_id: int) -> Optional[ProfileShare]:
    return db.query(ProfileShare).filter(
        ProfileShare.profile_id == profile_id,
        ProfileShare.is_active == True,
        ProfileShare.expires_at > datetime.utcnow()
    ).first()

def get_profile_share_by_token(db: Session, token: str) -> Optional[ProfileShare]:
    return db.query(ProfileShare).filter(
        ProfileShare.token == token
    ).first()

def revoke_profile_share(db: Session, token: str) -> Optional[ProfileShare]:
    share = get_profile_share_by_token(db, token)
    if share and share.is_active:
        share.is_active = False
        share.updated_at = datetime.utcnow()
        db.add(share)
        db.commit()
        db.refresh(share)
    return share
