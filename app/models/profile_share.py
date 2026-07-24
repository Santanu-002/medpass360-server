import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class ProfileShare(Base):
    __tablename__ = "profile_shares"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(String(36), ForeignKey("users.uid", ondelete="CASCADE"), nullable=False)
    
    token = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    max_uses = Column(Integer, nullable=True)  # None means unlimited
    uses_count = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    profile = relationship("Profile", back_populates="shares")
