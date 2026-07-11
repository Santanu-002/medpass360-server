import uuid
from sqlalchemy import Column, String, ForeignKey, Date, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(50), nullable=True)
    blood_type = Column(String(10), nullable=True)
    
    # Profile extras/metadata (allergies, medical history, etc.)
    allergies = Column(JSON, nullable=True)
    medical_conditions = Column(JSON, nullable=True)
    
    # Emergency Contact
    emergency_contact_name = Column(String(150), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 1-to-1 back-reference to User
    user = relationship("User", back_populates="profile")
