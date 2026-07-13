from sqlalchemy.orm import Session
from typing import Optional
from app.models import (
    User,
    Profile,
    Vital,
    EmergencyContact,
    Allergy,
    MedicalCondition,
    Medication,
    Lifestyle,
    FamilyHistory,
    AdditionalDetail,
)
from app.schemas.user import ProfileUpdate
from datetime import date


def get_user_by_id(db: Session, user_uid: str) -> Optional[User]:
    return db.query(User).filter(User.uid == user_uid).first()


def get_user_by_phone(db: Session, phone_number: str) -> Optional[User]:
    return db.query(User).filter(User.phone_number == phone_number).first()


def create_user(db: Session, phone_number: str) -> User:
    # Create the user
    db_user = User(phone_number=phone_number)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_profile(
    db: Session,
    user_uid: str,
    first_name: str,
    last_name: str,
    gender: str,
    date_of_birth: date,
    avatar: Optional[str] = None,
    phone_number: Optional[str] = None,
    email: Optional[str] = None
) -> Profile:
    db_profile = Profile(
        user_id=user_uid,
        first_name=first_name,
        last_name=last_name,
        gender=gender,
        date_of_birth=date_of_birth,
        avatar=avatar,
        phone_number=phone_number,
        email=email
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


def get_or_create_user(db: Session, phone_number: str) -> User:
    db_user = get_user_by_phone(db, phone_number)
    if not db_user:
        db_user = create_user(db, phone_number)
    return db_user


def update_profile(db: Session, user_uid: str, profile_update: ProfileUpdate) -> Optional[Profile]:
    db_profile = db.query(Profile).filter(Profile.user_id == user_uid).first()
    if not db_profile:
        # Fallback if profile didn't exist for some reason
        db_profile = Profile(user_id=user_uid)
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)

    # Exclude unset fields from the update dict
    update_data = profile_update.model_dump(exclude_unset=True)

    # 1. Update basic profile fields
    basic_fields = ["first_name", "last_name", "email", "phone_number", "date_of_birth", "gender", "avatar"]
    for key in basic_fields:
        if key in update_data:
            setattr(db_profile, key, update_data[key])

    # 2. Update Vitals (bloodType, height, weight)
    if "blood_type" in update_data or "medical_conditions" in update_data:
        if not db_profile.vitals_rel:
            db_profile.vitals_rel = Vital(profile_id=db_profile.id)
            db.add(db_profile.vitals_rel)
        
        if "blood_type" in update_data:
            db_profile.vitals_rel.blood_type = update_data["blood_type"]

        med_cond = update_data.get("medical_conditions")
        if med_cond and isinstance(med_cond, dict):
            if "height" in med_cond:
                db_profile.vitals_rel.height = med_cond["height"]
            if "weight" in med_cond:
                db_profile.vitals_rel.weight = med_cond["weight"]

    # 3. Update Emergency Contact
    if "emergency_contact_name" in update_data or "emergency_contact_phone" in update_data:
        if not db_profile.emergency_contact_rel:
            db_profile.emergency_contact_rel = EmergencyContact(profile_id=db_profile.id)
            db.add(db_profile.emergency_contact_rel)
        
        if "emergency_contact_name" in update_data:
            db_profile.emergency_contact_rel.name = update_data["emergency_contact_name"]
        if "emergency_contact_phone" in update_data:
            db_profile.emergency_contact_rel.phone = update_data["emergency_contact_phone"]

    # 4. Update Allergies
    if "allergies" in update_data:
        # Clear existing
        db.query(Allergy).filter(Allergy.profile_id == db_profile.id).delete()
        allergies_dict = update_data["allergies"]
        if allergies_dict and isinstance(allergies_dict, dict):
            for a_type in ["drug", "food", "environmental"]:
                names = allergies_dict.get(a_type, [])
                if names and isinstance(names, list):
                    for name in names:
                        db.add(Allergy(profile_id=db_profile.id, allergy_type=a_type, name=name))

    # 5. Update Medical Conditions, Medications, Lifestyle, Family History, Additional Details
    if "medical_conditions" in update_data:
        med_cond = update_data["medical_conditions"]
        if med_cond and isinstance(med_cond, dict):
            # Clear existing conditions
            db.query(MedicalCondition).filter(MedicalCondition.profile_id == db_profile.id).delete()
            durations = med_cond.get("durations", {}) or {}
            
            # Chronic conditions
            chronic = med_cond.get("chronicConditions", [])
            if chronic and isinstance(chronic, list):
                for name in chronic:
                    dur = durations.get(name)
                    db.add(MedicalCondition(profile_id=db_profile.id, condition_type="chronic", name=name, duration=dur))
            
            # Syndromes
            syndromes = med_cond.get("syndromes", [])
            if syndromes and isinstance(syndromes, list):
                for name in syndromes:
                    dur = durations.get(name)
                    db.add(MedicalCondition(profile_id=db_profile.id, condition_type="syndrome", name=name, duration=dur))

            # Medications
            db.query(Medication).filter(Medication.profile_id == db_profile.id).delete()
            meds = med_cond.get("currentMedications", [])
            if meds and isinstance(meds, list):
                for m in meds:
                    if isinstance(m, dict) and m.get("name"):
                        db.add(Medication(
                            profile_id=db_profile.id,
                            name=m["name"],
                            dosage=m.get("dosage"),
                            frequency=m.get("frequency")
                        ))

            # Lifestyle
            lifestyle_data = med_cond.get("lifestyle", {}) or {}
            history_data = med_cond.get("recentHistory", {}) or {}
            if lifestyle_data or history_data:
                if not db_profile.lifestyle_rel:
                    db_profile.lifestyle_rel = Lifestyle(profile_id=db_profile.id)
                    db.add(db_profile.lifestyle_rel)
                
                if "smoking" in lifestyle_data:
                    db_profile.lifestyle_rel.smoking = lifestyle_data["smoking"]
                if "alcohol" in lifestyle_data:
                    db_profile.lifestyle_rel.alcohol = lifestyle_data["alcohol"]
                if "physicalActivity" in lifestyle_data:
                    db_profile.lifestyle_rel.physical_activity = lifestyle_data["physicalActivity"]
                
                if "lastDoctorVisit" in history_data and history_data["lastDoctorVisit"]:
                    try:
                        visit_date = date.fromisoformat(history_data["lastDoctorVisit"])
                        db_profile.lifestyle_rel.last_doctor_visit = visit_date
                    except ValueError:
                        pass
                if "visitReason" in history_data:
                    db_profile.lifestyle_rel.visit_reason = history_data["visitReason"]
                if "recentSurgeries" in history_data:
                    db_profile.lifestyle_rel.recent_surgeries = history_data["recentSurgeries"]

            # Family History
            db.query(FamilyHistory).filter(FamilyHistory.profile_id == db_profile.id).delete()
            fam = med_cond.get("familyHistory", [])
            if fam and isinstance(fam, list):
                for name in fam:
                    db.add(FamilyHistory(profile_id=db_profile.id, name=name))

            # Additional notes
            notes = med_cond.get("additionalNotes", "")
            if notes is not None:
                if not db_profile.additional_detail_rel:
                    db_profile.additional_detail_rel = AdditionalDetail(profile_id=db_profile.id)
                    db.add(db_profile.additional_detail_rel)
                db_profile.additional_detail_rel.additional_notes = notes

    db.commit()
    db.refresh(db_profile)
    return db_profile

