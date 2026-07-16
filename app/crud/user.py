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

    # 2. Update Vitals (blood_type, height, weight)
    if "vitals" in update_data and update_data["vitals"]:
        vitals_data = update_data["vitals"]
        if not db_profile.vitals_rel:
            db_profile.vitals_rel = Vital(profile_id=db_profile.id)
            db.add(db_profile.vitals_rel)
        if "blood_type" in vitals_data:
            db_profile.vitals_rel.blood_type = vitals_data["blood_type"]
        if "height" in vitals_data and vitals_data["height"]:
            h = vitals_data["height"]
            unit_val = h['unit'].value if hasattr(h['unit'], 'value') else h['unit']
            db_profile.vitals_rel.height = f"{h['value']} {unit_val}"
        if "weight" in vitals_data and vitals_data["weight"]:
            w = vitals_data["weight"]
            unit_val = w['unit'].value if hasattr(w['unit'], 'value') else w['unit']
            db_profile.vitals_rel.weight = f"{w['value']} {unit_val}"


    # 3. Update Emergency Contact
    if "emergency_contact" in update_data and update_data["emergency_contact"]:
        contact_data = update_data["emergency_contact"]
        if not db_profile.emergency_contact_rel:
            db_profile.emergency_contact_rel = EmergencyContact(profile_id=db_profile.id)
            db.add(db_profile.emergency_contact_rel)
        if "name" in contact_data:
            db_profile.emergency_contact_rel.name = contact_data["name"]
        if "phone" in contact_data:
            db_profile.emergency_contact_rel.phone = contact_data["phone"]

    # 4. Update Allergies
    if "allergies" in update_data:
        db.query(Allergy).filter(Allergy.profile_id == db_profile.id).delete()
        allergies_dict = update_data["allergies"]
        if allergies_dict and isinstance(allergies_dict, dict):
            for a_type in ["drug", "food", "environmental"]:
                items = allergies_dict.get(a_type, [])
                if items and isinstance(items, list):
                    for item in items:
                        name = item["displayName"]
                        db.add(Allergy(profile_id=db_profile.id, allergy_type=a_type, name=name))

    # 5. Update Conditions (Chronic, Syndromes, Durations)
    if any(k in update_data for k in ["chronic_conditions", "syndromes", "durations"]):
        db.query(MedicalCondition).filter(MedicalCondition.profile_id == db_profile.id).delete()
        durations = update_data.get("durations") or {}
        
        chronic = update_data.get("chronic_conditions") or []
        for item in chronic:
            name = item["displayName"]
            dur = durations.get(name)
            db.add(MedicalCondition(profile_id=db_profile.id, condition_type="chronic", name=name, duration=dur))
            
        syndromes = update_data.get("syndromes") or []
        for item in syndromes:
            name = item["displayName"]
            dur = durations.get(name)
            db.add(MedicalCondition(profile_id=db_profile.id, condition_type="syndrome", name=name, duration=dur))

    # 6. Update Lifestyle
    if "lifestyle" in update_data and update_data["lifestyle"]:
        ls = update_data["lifestyle"]
        if not db_profile.lifestyle_rel:
            db_profile.lifestyle_rel = Lifestyle(profile_id=db_profile.id)
            db.add(db_profile.lifestyle_rel)
        if "smoking" in ls:
            db_profile.lifestyle_rel.smoking = ls["smoking"]
        if "alcohol" in ls:
            db_profile.lifestyle_rel.alcohol = ls["alcohol"]
        if "physical_activity" in ls:
            db_profile.lifestyle_rel.physical_activity = ls["physical_activity"]

    # 7. Update Recent History
    if "recent_history" in update_data and update_data["recent_history"]:
        rh = update_data["recent_history"]
        if not db_profile.lifestyle_rel:
            db_profile.lifestyle_rel = Lifestyle(profile_id=db_profile.id)
            db.add(db_profile.lifestyle_rel)
        if "last_doctor_visit" in rh and rh["last_doctor_visit"]:
            try:
                visit_date = date.fromisoformat(rh["last_doctor_visit"])
                db_profile.lifestyle_rel.last_doctor_visit = visit_date
            except ValueError:
                pass
        if "visit_reason" in rh:
            db_profile.lifestyle_rel.visit_reason = rh["visit_reason"]
        if "recent_surgeries" in rh:
            db_profile.lifestyle_rel.recent_surgeries = rh["recent_surgeries"]

    # 8. Update Family History
    if "family_history" in update_data:
        db.query(FamilyHistory).filter(FamilyHistory.profile_id == db_profile.id).delete()
        fam = update_data["family_history"] or []
        for item in fam:
            db.add(FamilyHistory(profile_id=db_profile.id, name=item["displayName"]))

    # 9. Update Additional Notes
    if "additional_notes" in update_data:
        notes = update_data["additional_notes"]
        if notes is not None:
            if not db_profile.additional_detail_rel:
                db_profile.additional_detail_rel = AdditionalDetail(profile_id=db_profile.id)
                db.add(db_profile.additional_detail_rel)
            db_profile.additional_detail_rel.additional_notes = notes

    # 10. Update Medications
    if "current_medications" in update_data:
        db.query(Medication).filter(Medication.profile_id == db_profile.id).delete()
        meds = update_data["current_medications"] or []
        for m in meds:
            db.add(Medication(
                profile_id=db_profile.id,
                name=m["name"],
                slug=m.get("slug"),
                dosage=m.get("dosage"),
                frequency=m.get("frequency"),
                timings=m.get("timings"),
                instructions=m.get("instructions"),
                food_relation=m.get("foodRelation"),
                tags=m.get("tags")
            ))

    db.commit()
    db.refresh(db_profile)
    return db_profile



def get_user_by_identity(db: Session, identity: str) -> Optional[User]:
    """
    Check if a user exists by a given identity (either primary phone number on User, 
    or email/secondary phone number on Profile).
    Returns the User model if found, else None.
    """
    # 1. Check primary phone number in User
    user = db.query(User).filter(User.phone_number == identity).first()
    if user:
        return user
    
    # 2. Check email or phone number in Profile
    db_profile = db.query(Profile).filter(
        (Profile.email == identity) | (Profile.phone_number == identity)
    ).first()
    if db_profile:
        return db.query(User).filter(User.uid == db_profile.user_id).first()
        
    return None


def enable_user_biometrics(db: Session, user: User) -> User:
    """Enables biometric login flags on User and persists it."""
    user.has_biometrics = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


