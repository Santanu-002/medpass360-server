import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class ProfileAccess(Base):
    __tablename__ = "profile_access"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.uid", ondelete="CASCADE"), nullable=False, index=True)
    
    access_level = Column(String(50), nullable=False, default="view_only")  # owner, full_access, care_partner, view_only
    relation = Column(String(50), nullable=False, default="other")  # self, son, daughter, spouse, parent, friend, etc.
    
    granted_by = Column(String(36), ForeignKey("users.uid", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by = Column(String(36), ForeignKey("users.uid", ondelete="SET NULL"), nullable=True)

    # Relationships
    profile = relationship("Profile", back_populates="access_list")
