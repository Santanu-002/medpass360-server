import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    phone_number = Column(String(150), unique=True, nullable=True, index=True)
    email = Column(String(150), unique=True, nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_agreed_to_terms = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 1-to-1 relationship with Profile
    profile = relationship("Profile", uselist=False, back_populates="user", cascade="all, delete-orphan", foreign_keys="[Profile.user_id]")
    created_profiles = relationship("Profile", back_populates="creator", foreign_keys="[Profile.created_by]")
    device_biometrics = relationship("UserDeviceBiometric", back_populates="user", cascade="all, delete-orphan")

    @property
    def profiles(self):
        from sqlalchemy.orm import object_session
        db = object_session(self)
        if not db:
            return []
        
        from app.models.profile_access import ProfileAccess
        access_records = db.query(ProfileAccess).filter(
            ProfileAccess.user_id == self.uid,
            ProfileAccess.revoked_at.is_(None)
        ).all()
        
        # Sort access records so the user's own profile (relation == "self" or access_level == "owner") is first,
        # followed by other records sorted by created_at.
        def sort_key(rec):
            if rec.relation == "self" or rec.access_level == "owner":
                return (0, rec.created_at or 0)
            return (1, rec.created_at or 0)
            
        access_records_sorted = sorted(access_records, key=sort_key)
        
        res = []
        seen_uids = set()
        for record in access_records_sorted:
            p = record.profile
            if p and p.uid not in seen_uids:
                p.temp_relation = record.relation
                p.temp_access_level = record.access_level
                res.append(p)
                seen_uids.add(p.uid)
        return res



    @property
    def is_biometric_setup_completed(self) -> bool:
        return any(db.is_enabled for db in self.device_biometrics)

