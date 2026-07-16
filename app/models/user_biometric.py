import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class UserDeviceBiometric(Base):
    __tablename__ = "user_device_biometrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.uid", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(200), nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    enabled_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    disabled_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship back to User
    user = relationship("User", back_populates="device_biometrics")
