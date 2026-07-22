import uuid
from sqlalchemy import Column, String, ForeignKey, Date, DateTime, Integer, JSON, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship, object_session
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
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(50), nullable=True)
    avatar = Column(String(500), nullable=True)
    
    created_by = Column(String(36), ForeignKey("users.uid", ondelete="SET NULL"), nullable=True)
    _relation = Column("relation", String(50), nullable=False, default="self")
    is_verified = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 1-to-1 back-reference to User
    user = relationship("User", back_populates="profile", foreign_keys=[user_id])
    creator = relationship("User", back_populates="created_profiles", foreign_keys=[created_by])

    # Access control permissions list
    access_list = relationship("ProfileAccess", back_populates="profile", cascade="all, delete-orphan")

    # 1-to-1 and 1-to-many child relationships
    vitals_rel = relationship("Vital", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    emergency_contact_rel = relationship("EmergencyContact", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    medical_selections_rel = relationship("ProfileMedicalSelection", back_populates="profile", cascade="all, delete-orphan")
    medications_rel = relationship("Medication", back_populates="profile", cascade="all, delete-orphan")
    lifestyle_rel = relationship("Lifestyle", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    additional_detail_rel = relationship("AdditionalDetail", back_populates="profile", uselist=False, cascade="all, delete-orphan")

    @property
    def email(self) -> Optional[str]:
        return self.user.email if self.user else None

    @property
    def phone_number(self) -> Optional[str]:
        return self.user.phone_number if self.user else None

    @property
    def relation(self) -> str:
        if hasattr(self, "temp_relation") and self.temp_relation is not None:
            return self.temp_relation
        return self._relation

    @relation.setter
    def relation(self, value: str):
        self._relation = value

    @property
    def access_level(self) -> Optional[str]:
        return getattr(self, "temp_access_level", None)

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
        db = object_session(self)
        if not db:
            return {"drug": [], "food": [], "environmental": []}
            
        drug_uids = [sel.item_uid for sel in self.medical_selections_rel if sel.category == "drug_allergy"]
        food_uids = [sel.item_uid for sel in self.medical_selections_rel if sel.category == "food_allergy"]
        env_uids = [sel.item_uid for sel in self.medical_selections_rel if sel.category == "environmental_allergy"]
        
        all_uids = drug_uids + food_uids + env_uids
        if not all_uids:
            return {"drug": [], "food": [], "environmental": []}
            
        items = db.query(Allergy).filter(Allergy.uid.in_(all_uids)).all()
        items_by_uid = {i.uid: i.display_name for i in items}
        
        drug = [{"uid": uid, "displayName": items_by_uid[uid]} for uid in drug_uids if uid in items_by_uid]
        food = [{"uid": uid, "displayName": items_by_uid[uid]} for uid in food_uids if uid in items_by_uid]
        env = [{"uid": uid, "displayName": items_by_uid[uid]} for uid in env_uids if uid in items_by_uid]
        
        return {
            "drug": drug,
            "food": food,
            "environmental": env
        }

    @property
    def chronic_conditions(self) -> List[dict]:
        db = object_session(self)
        if not db:
            return []
        uids = [sel.item_uid for sel in self.medical_selections_rel if sel.category == "chronic_condition"]
        if not uids:
            return []
        items = db.query(MedicalCondition).filter(MedicalCondition.uid.in_(uids)).all()
        return [{"uid": i.uid, "displayName": i.display_name} for i in items]

    @property
    def syndromes(self) -> List[dict]:
        db = object_session(self)
        if not db:
            return []
        uids = [sel.item_uid for sel in self.medical_selections_rel if sel.category == "syndrome"]
        if not uids:
            return []
        items = db.query(MedicalCondition).filter(MedicalCondition.uid.in_(uids)).all()
        return [{"uid": i.uid, "displayName": i.display_name} for i in items]

    @property
    def durations(self) -> dict:
        db = object_session(self)
        if not db:
            return {}
        selections = [sel for sel in self.medical_selections_rel if sel.category in ["chronic_condition", "syndrome"] and sel.duration]
        if not selections:
            return {}
        uids = [sel.item_uid for sel in selections]
        items = db.query(MedicalCondition).filter(MedicalCondition.uid.in_(uids)).all()
        name_by_uid = {i.uid: i.display_name for i in items}
        return {name_by_uid[sel.item_uid]: sel.duration for sel in selections if sel.item_uid in name_by_uid}

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
        db = object_session(self)
        if not db:
            return []
        uids = [sel.item_uid for sel in self.medical_selections_rel if sel.category == "family_history"]
        if not uids:
            return []
        items = db.query(FamilyHistory).filter(FamilyHistory.uid.in_(uids)).all()
        return [{"uid": i.uid, "displayName": i.display_name} for i in items]

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
            "tags": m.tags or [],
            "isStopped": bool(m.is_stopped) if hasattr(m, "is_stopped") and m.is_stopped is not None else ("STOPPED" in (m.tags or []))
        } for m in self.medications_rel]

    @property
    def health_profile(self) -> dict:
        return {
            "vitals": self.vitals,
            "emergency_contact": self.emergency_contact,
            "allergies": self.allergies,
            "chronic_conditions": self.chronic_conditions,
            "syndromes": self.syndromes,
            "durations": self.durations,
            "lifestyle": self.lifestyle,
            "recent_history": self.recent_history,
            "family_history": self.family_history,
            "additional_notes": self.additional_notes,
            "current_medications": self.current_medications,
        }




class Vital(Base):
    __tablename__ = "vitals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    blood_type = Column(String(10), nullable=True)
    height = Column(String(50), nullable=True)
    weight = Column(String(50), nullable=True)
    created_by = Column(String(36), ForeignKey("users.uid", ondelete="SET NULL"), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    profile = relationship("Profile", back_populates="vitals_rel")


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=True)
    phone = Column(String(20), nullable=True)
    created_by = Column(String(36), ForeignKey("users.uid", ondelete="SET NULL"), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    profile = relationship("Profile", back_populates="emergency_contact_rel")


class Allergy(Base):
    __tablename__ = "allergies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    allergy_type = Column(String(50), nullable=False)  # 'drug', 'food', 'environmental'
    slug = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    created_by = Column(String(36), ForeignKey("users.uid", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="active")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('allergy_type', 'slug', name='uq_allergies_type_slug'),
    )


class MedicalCondition(Base):
    __tablename__ = "medical_conditions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    condition_type = Column(String(50), nullable=False)  # 'chronic', 'syndrome'
    slug = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    created_by = Column(String(36), ForeignKey("users.uid", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="active")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('condition_type', 'slug', name='uq_conditions_type_slug'),
    )


class FamilyHistory(Base):
    __tablename__ = "family_histories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    created_by = Column(String(36), ForeignKey("users.uid", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="active")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('slug', name='uq_family_histories_slug'),
    )


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
    is_stopped = Column(Boolean, default=False, nullable=True)
    created_by = Column(String(36), ForeignKey("users.uid", ondelete="SET NULL"), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

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
    created_by = Column(String(36), ForeignKey("users.uid", ondelete="SET NULL"), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    profile = relationship("Profile", back_populates="lifestyle_rel")



class AdditionalDetail(Base):
    __tablename__ = "additional_details"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    insurance_provider = Column(String(150), nullable=True)
    primary_physician = Column(String(150), nullable=True)
    additional_notes = Column(String(1000), nullable=True)
    created_by = Column(String(36), ForeignKey("users.uid", ondelete="SET NULL"), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    profile = relationship("Profile", back_populates="additional_detail_rel")


class ProfileMedicalSelection(Base):
    __tablename__ = "profile_medical_selections"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    item_uid = Column(String(36), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    duration = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    profile = relationship("Profile", back_populates="medical_selections_rel")
