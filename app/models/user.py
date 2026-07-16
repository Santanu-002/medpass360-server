import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    phone_number = Column(String(150), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 1-to-1 relationship with Profile
    profile = relationship("Profile", uselist=False, back_populates="user", cascade="all, delete-orphan", foreign_keys="[Profile.user_id]")
    created_profiles = relationship("Profile", back_populates="creator", foreign_keys="[Profile.created_by]")
    device_biometrics = relationship("UserDeviceBiometric", back_populates="user", cascade="all, delete-orphan")

    @property
    def profiles(self):
        res = []
        seen_uids = set()
        if self.profile:
            res.append(self.profile)
            seen_uids.add(self.profile.uid)
        for p in self.created_profiles:
            if p.uid not in seen_uids:
                res.append(p)
                seen_uids.add(p.uid)
        return res

    @property
    def is_profile_completed(self) -> bool:
        return self.profile is not None

    @property
    def is_health_profile_completed(self) -> bool:
        if not self.profile:
            return False
        # Check own profile
        if (
            self.profile.vitals_rel is not None or 
            self.profile.emergency_contact_rel is not None or
            len(self.profile.allergies_rel) > 0 or
            len(self.profile.conditions_rel) > 0 or
            len(self.profile.medications_rel) > 0 or
            self.profile.lifestyle_rel is not None or
            len(self.profile.family_history_rel) > 0 or
            self.profile.additional_detail_rel is not None
        ):
            return True

        # Check other profiles created by this user
        for p in self.created_profiles:
            if p.uid != self.profile.uid:
                if (
                    p.vitals_rel is not None or
                    p.emergency_contact_rel is not None or
                    len(p.allergies_rel) > 0 or
                    len(p.conditions_rel) > 0 or
                    len(p.medications_rel) > 0 or
                    p.lifestyle_rel is not None or
                    len(p.family_history_rel) > 0 or
                    p.additional_detail_rel is not None
                ):
                    return True
        return False

    @property
    def is_biometric_setup_completed(self) -> bool:
        return any(db.is_enabled for db in self.device_biometrics)

