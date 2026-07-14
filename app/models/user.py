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
    has_biometrics = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 1-to-1 relationship with Profile
    profile = relationship("Profile", uselist=False, back_populates="user", cascade="all, delete-orphan")

    @property
    def is_profile_completed(self) -> bool:
        return self.profile is not None

    @property
    def is_health_profile_completed(self) -> bool:
        if not self.profile:
            return False
        return (
            self.profile.vitals_rel is not None or 
            self.profile.emergency_contact_rel is not None or
            len(self.profile.allergies_rel) > 0 or
            len(self.profile.conditions_rel) > 0 or
            len(self.profile.medications_rel) > 0 or
            self.profile.lifestyle_rel is not None or
            len(self.profile.family_history_rel) > 0 or
            self.profile.additional_detail_rel is not None
        )

    @property
    def is_biometric_setup_completed(self) -> bool:
        return self.has_biometrics

