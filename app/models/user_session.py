from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(150), nullable=False, index=True)
    device_model = Column(String(150), nullable=True)
    os_version = Column(String(150), nullable=True)
    platform = Column(String(150), nullable=True)
    refresh_token = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship back to User
    user = relationship("User", backref="sessions")
