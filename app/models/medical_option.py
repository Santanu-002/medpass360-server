import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Index
from sqlalchemy.sql import func
from app.core.database import Base

class MedicalOption(Base):
    __tablename__ = "medical_options"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    category = Column(String(50), nullable=False, index=True)
    slug = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    created_by = Column(String(36), ForeignKey("users.uid", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="active")  # "active" or "inactive"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes for optimized lookups and grouping
    __table_args__ = (
        Index("ix_medical_options_category_status", "category", "status"),
    )
