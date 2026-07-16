import uuid
from sqlalchemy import Column, String, ForeignKey, Date, DateTime, Integer, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from typing import Optional, List

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.uid", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    phone_number = Column(String(50), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(50), nullable=True)
    avatar = Column(String(500), nullable=True)
    
    created_by = Column(String(36), ForeignKey("users.uid", ondelete="SET NULL"), nullable=True)
    relation = Column(String(50), nullable=False, default="self")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 1-to-1 back-reference to User
    user = relationship("User", back_populates="profile", foreign_keys=[user_id])
    creator = relationship("User", back_populates="created_profiles", foreign_keys=[created_by])

    # 1-to-1 and 1-to-many child relationships
    vitals_rel = relationship("Vital", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    emergency_contact_rel = relationship("EmergencyContact", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    allergies_rel = relationship("Allergy", back_populates="profile", cascade="all, delete-orphan")
    conditions_rel = relationship("MedicalCondition", back_populates="profile", cascade="all, delete-orphan")
    medications_rel = relationship("Medication", back_populates="profile", cascade="all, delete-orphan")
    lifestyle_rel = relationship("Lifestyle", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    family_history_rel = relationship("FamilyHistory", back_populates="profile", cascade="all, delete-orphan")
    additional_detail_rel = relationship("AdditionalDetail", back_populates="profile", uselist=False, cascade="all, delete-orphan")

    @property
    def vitals(self) -> Optional[dict]:
        if not self.vitals_rel:
            return None
        
        height_data = None
        if self.vitals_rel.height:
            parts = self.vitals_rel.height.split(" ", 1)
            if len(parts) == 2:
                height_data = {"value": parts[0], "unit": parts[1]}
            else:
                height_data = {"value": parts[0], "unit": "cm"}
                
        weight_data = None
        if self.vitals_rel.weight:
            parts = self.vitals_rel.weight.split(" ", 1)
            if len(parts) == 2:
                weight_data = {"value": parts[0], "unit": parts[1]}
            else:
                weight_data = {"value": parts[0], "unit": "kg"}

        return {
            "bloodType": self.vitals_rel.blood_type,
            "height": height_data,
            "weight": weight_data
        }

    @property
    def emergency_contact(self) -> Optional[dict]:
        if not self.emergency_contact_rel:
            return None
        return {
            "name": self.emergency_contact_rel.name,
            "phone": self.emergency_contact_rel.phone
        }

    @property
    def allergies(self) -> Optional[dict]:
        drug = [{"uid": str(a.id), "displayName": a.name} for a in self.allergies_rel if a.allergy_type == "drug"]
        food = [{"uid": str(a.id), "displayName": a.name} for a in self.allergies_rel if a.allergy_type == "food"]
        env = [{"uid": str(a.id), "displayName": a.name} for a in self.allergies_rel if a.allergy_type == "environmental"]
        return {
            "drug": drug,
            "food": food,
            "environmental": env
        }

    @property
    def chronic_conditions(self) -> List[dict]:
        return [{"uid": str(c.id), "displayName": c.name} for c in self.conditions_rel if c.condition_type == "chronic"]

    @property
    def syndromes(self) -> List[dict]:
        return [{"uid": str(c.id), "displayName": c.name} for c in self.conditions_rel if c.condition_type == "syndrome"]

    @property
    def durations(self) -> dict:
        return {c.name: c.duration for c in self.conditions_rel if c.duration}

    @property
    def lifestyle(self) -> Optional[dict]:
        if not self.lifestyle_rel:
            return None
        return {
            "smoking": self.lifestyle_rel.smoking,
            "alcohol": self.lifestyle_rel.alcohol,
            "physicalActivity": self.lifestyle_rel.physical_activity
        }

    @property
    def recent_history(self) -> Optional[dict]:
        if not self.lifestyle_rel:
            return None
        return {
            "lastDoctorVisit": self.lifestyle_rel.last_doctor_visit.isoformat() if self.lifestyle_rel.last_doctor_visit else None,
            "visitReason": self.lifestyle_rel.visit_reason,
            "recentSurgeries": self.lifestyle_rel.recent_surgeries
        }

    @property
    def family_history(self) -> List[dict]:
        return [{"uid": str(f.id), "displayName": f.name} for f in self.family_history_rel]

    @property
    def additional_notes(self) -> str:
        return self.additional_detail_rel.additional_notes if self.additional_detail_rel else ""

    @property
    def current_medications(self) -> List[dict]:
        return [{
            "uid": str(m.id),
            "name": m.name,
            "slug": m.slug,
            "dosage": m.dosage,
            "frequency": m.frequency,
            "timings": m.timings,
            "instructions": m.instructions,
            "foodRelation": m.food_relation,
            "tags": m.tags
        } for m in self.medications_rel]



class Vital(Base):
    __tablename__ = "vitals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    blood_type = Column(String(10), nullable=True)
    height = Column(String(50), nullable=True)
    weight = Column(String(50), nullable=True)

    profile = relationship("Profile", back_populates="vitals_rel")


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=True)
    phone = Column(String(20), nullable=True)

    profile = relationship("Profile", back_populates="emergency_contact_rel")


class Allergy(Base):
    __tablename__ = "allergies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    allergy_type = Column(String(50), nullable=False)  # 'drug', 'food', 'environmental'
    name = Column(String(100), nullable=False)

    profile = relationship("Profile", back_populates="allergies_rel")


class MedicalCondition(Base):
    __tablename__ = "medical_conditions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    condition_type = Column(String(50), nullable=False)  # 'chronic', 'syndrome'
    name = Column(String(100), nullable=False)
    duration = Column(String(50), nullable=True)

    profile = relationship("Profile", back_populates="conditions_rel")


class Medication(Base):
    __tablename__ = "medications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    slug = Column(String(150), nullable=True)
    dosage = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)
    
    # New columns
    timings = Column(JSON, nullable=True)
    instructions = Column(String(255), nullable=True)
    food_relation = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)

    profile = relationship("Profile", back_populates="medications_rel")



class Lifestyle(Base):
    __tablename__ = "lifestyles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    smoking = Column(String(50), nullable=True)
    alcohol = Column(String(50), nullable=True)
    physical_activity = Column(String(50), nullable=True)
    last_doctor_visit = Column(Date, nullable=True)
    visit_reason = Column(String(255), nullable=True)
    recent_surgeries = Column(String(255), nullable=True)

    profile = relationship("Profile", back_populates="lifestyle_rel")


class FamilyHistory(Base):
    __tablename__ = "family_histories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)

    profile = relationship("Profile", back_populates="family_history_rel")


class AdditionalDetail(Base):
    __tablename__ = "additional_details"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    insurance_provider = Column(String(150), nullable=True)
    primary_physician = Column(String(150), nullable=True)
    additional_notes = Column(String(1000), nullable=True)

    profile = relationship("Profile", back_populates="additional_detail_rel")
