from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime
from fastapi import HTTPException, status
from app.models import (
    User,
    UserSession,
    UserDeviceBiometric,
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


def get_user_by_id(db: Session, user_uid: str) -> Optional[User]:
    return db.query(User).filter(User.uid == user_uid).first()


def get_user_by_phone(db: Session, phone_number: str) -> Optional[User]:
    return db.query(User).filter(User.phone_number == phone_number).first()


def create_user(db: Session, identity: str) -> User:
    # Create the user depending on identity format (email or phone)
    if "@" in identity:
        db_user = User(email=identity, phone_number=None)
    else:
        db_user = User(phone_number=identity, email=None)
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
    email: Optional[str] = None,
    created_by: Optional[str] = None,
    relation: str = "self"
) -> Profile:
    db_profile = Profile(
        user_id=user_uid,
        first_name=first_name,
        last_name=last_name,
        gender=gender,
        date_of_birth=date_of_birth,
        avatar=avatar,
        phone_number=phone_number,
        email=email,
        created_by=created_by or user_uid,
        relation=relation,
        is_verified=True if relation == "self" else False
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


def get_or_create_user(db: Session, identity: str) -> User:
    db_user = get_user_by_identity(db, identity)
    if not db_user:
        db_user = create_user(db, identity)
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

    # Determine which profile we are actually updating
    target_profile = db_profile
    if profile_update.profile_target == 'other' and profile_update.care_person:
        care = profile_update.care_person
        identity = care.get("identity")
        if identity:
            care_user = get_user_by_identity(db, identity)
            if care_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A user with this phone number or email already exists."
                )
            
            # Create a new user
            care_user = User(phone_number=identity)
            db.add(care_user)
            db.commit()
            db.refresh(care_user)
            
            # 2. Look up profile of this care_user
            care_profile = db.query(Profile).filter(Profile.user_id == care_user.uid).first()
            if not care_profile:
                name_parts = care.get("name", "").split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""
                dob_val = None
                if care.get("dob"):
                    try:
                        dob_val = date.fromisoformat(care["dob"])
                    except ValueError:
                        pass
                
                care_profile = Profile(
                    user_id=care_user.uid,
                    first_name=first_name,
                    last_name=last_name,
                    gender=care.get("gender"),
                    date_of_birth=dob_val,
                    avatar=care.get("avatar"),
                    phone_number=care.get("phoneNumber") or (identity if "@" not in identity else None),
                    email=care.get("email") or (identity if "@" in identity else None),
                    created_by=user_uid,
                    relation=care.get("relation", "other"),
                    is_verified=False
                )
                db.add(care_profile)
                db.commit()
                db.refresh(care_profile)
            else:
                # Update care profile details
                name_parts = care.get("name", "").split(" ", 1)
                if name_parts:
                    care_profile.first_name = name_parts[0]
                    if len(name_parts) > 1:
                        care_profile.last_name = name_parts[1]
                if care.get("gender"):
                    care_profile.gender = care.get("gender")
                if care.get("dob"):
                    try:
                        care_profile.date_of_birth = date.fromisoformat(care["dob"])
                    except ValueError:
                        pass
                if care.get("avatar"):
                    care_profile.avatar = care.get("avatar")
                if care.get("email"):
                    care_profile.email = care.get("email")
                if care.get("phoneNumber"):
                    care_profile.phone_number = care.get("phoneNumber")
                care_profile.created_by = user_uid
                care_profile.relation = care.get("relation", care_profile.relation or "other")
                db.add(care_profile)
                db.commit()
                db.refresh(care_profile)
            
            target_profile = care_profile
    else:
        db_profile.relation = "self"
        db_profile.created_by = user_uid

    # 1. Update basic profile fields (only if not 'other', since we set care person's details above)
    if profile_update.profile_target != 'other':
        basic_fields = ["first_name", "last_name", "email", "phone_number", "date_of_birth", "gender", "avatar"]
        for key in basic_fields:
            if key in update_data:
                setattr(target_profile, key, update_data[key])

    # Helpers to support both nested health_profile and flat properties in the request payload
    def has_health_field(field_name: str) -> bool:
        if "health_profile" in update_data and update_data["health_profile"] is not None:
            return field_name in update_data["health_profile"]
        return field_name in update_data

    def get_health_field(field_name: str):
        if "health_profile" in update_data and update_data["health_profile"] is not None:
            return update_data["health_profile"].get(field_name)
        return update_data.get(field_name)

    # 2. Update Vitals (blood_type, height, weight)
    if has_health_field("vitals") and get_health_field("vitals"):
        vitals_data = get_health_field("vitals")
        if not target_profile.vitals_rel:
            target_profile.vitals_rel = Vital(profile_id=target_profile.id, created_by=user_uid)
            db.add(target_profile.vitals_rel)
        else:
            target_profile.vitals_rel.updated_at = func.now()
        if "blood_type" in vitals_data:
            target_profile.vitals_rel.blood_type = vitals_data["blood_type"]
        if "height" in vitals_data and vitals_data["height"]:
            h = vitals_data["height"]
            unit_val = h['unit'].value if hasattr(h['unit'], 'value') else h['unit']
            target_profile.vitals_rel.height = f"{h['value']} {unit_val}"
        if "weight" in vitals_data and vitals_data["weight"]:
            w = vitals_data["weight"]
            unit_val = w['unit'].value if hasattr(w['unit'], 'value') else w['unit']
            target_profile.vitals_rel.weight = f"{w['value']} {unit_val}"

    # 3. Update Emergency Contact
    if has_health_field("emergency_contact") and get_health_field("emergency_contact"):
        contact_data = get_health_field("emergency_contact")
        if not target_profile.emergency_contact_rel:
            target_profile.emergency_contact_rel = EmergencyContact(profile_id=target_profile.id, created_by=user_uid)
            db.add(target_profile.emergency_contact_rel)
        else:
            target_profile.emergency_contact_rel.updated_at = func.now()
        if "name" in contact_data:
            target_profile.emergency_contact_rel.name = contact_data["name"]
        if "phone" in contact_data:
            target_profile.emergency_contact_rel.phone = contact_data["phone"]

    # 4. Update Allergies
    if has_health_field("allergies"):
        db.query(Allergy).filter(Allergy.profile_id == target_profile.id).delete()
        allergies_dict = get_health_field("allergies")
        if allergies_dict and isinstance(allergies_dict, dict):
            from app.core.utils import slugify
            for a_type in ["drug", "food", "environmental"]:
                items = allergies_dict.get(a_type, [])
                if items and isinstance(items, list):
                    for item in items:
                        name = item["displayName"]
                        slug = slugify(name)
                        db.add(Allergy(
                            profile_id=target_profile.id,
                            allergy_type=a_type,
                            slug=slug,
                            display_name=name,
                            created_by=user_uid,
                            status="active"
                        ))

    # 5. Update Conditions (Chronic, Syndromes, Durations)
    if any(has_health_field(k) for k in ["chronic_conditions", "syndromes", "durations"]):
        db.query(MedicalCondition).filter(MedicalCondition.profile_id == target_profile.id).delete()
        durations = get_health_field("durations") or {}
        from app.core.utils import slugify
        
        chronic = get_health_field("chronic_conditions") or []
        for item in chronic:
            name = item["displayName"]
            slug = slugify(name)
            dur = durations.get(name)
            db.add(MedicalCondition(
                profile_id=target_profile.id,
                condition_type="chronic",
                slug=slug,
                display_name=name,
                created_by=user_uid,
                status="active",
                duration=dur
            ))
            
        syndromes = get_health_field("syndromes") or []
        for item in syndromes:
            name = item["displayName"]
            slug = slugify(name)
            dur = durations.get(name)
            db.add(MedicalCondition(
                profile_id=target_profile.id,
                condition_type="syndrome",
                slug=slug,
                display_name=name,
                created_by=user_uid,
                status="active",
                duration=dur
            ))

    # 6. Update Lifestyle
    if has_health_field("lifestyle") and get_health_field("lifestyle"):
        ls = get_health_field("lifestyle")
        if not target_profile.lifestyle_rel:
            target_profile.lifestyle_rel = Lifestyle(profile_id=target_profile.id, created_by=user_uid)
            db.add(target_profile.lifestyle_rel)
        else:
            target_profile.lifestyle_rel.updated_at = func.now()
        if "smoking" in ls:
            target_profile.lifestyle_rel.smoking = ls["smoking"]
        if "alcohol" in ls:
            target_profile.lifestyle_rel.alcohol = ls["alcohol"]
        if "physical_activity" in ls:
            target_profile.lifestyle_rel.physical_activity = ls["physical_activity"]

    # 7. Update Recent History
    if has_health_field("recent_history") and get_health_field("recent_history"):
        rh = get_health_field("recent_history")
        if not target_profile.lifestyle_rel:
            target_profile.lifestyle_rel = Lifestyle(profile_id=target_profile.id, created_by=user_uid)
            db.add(target_profile.lifestyle_rel)
        else:
            target_profile.lifestyle_rel.updated_at = func.now()
        if "last_doctor_visit" in rh and rh["last_doctor_visit"]:
            try:
                visit_date = date.fromisoformat(rh["last_doctor_visit"])
                target_profile.lifestyle_rel.last_doctor_visit = visit_date
            except ValueError:
                pass
        if "visit_reason" in rh:
            target_profile.lifestyle_rel.visit_reason = rh["visit_reason"]
        if "recent_surgeries" in rh:
            target_profile.lifestyle_rel.recent_surgeries = rh["recent_surgeries"]

    # 8. Update Family History
    if has_health_field("family_history"):
        db.query(FamilyHistory).filter(FamilyHistory.profile_id == target_profile.id).delete()
        fam = get_health_field("family_history") or []
        from app.core.utils import slugify
        for item in fam:
            name = item["displayName"]
            slug = slugify(name)
            db.add(FamilyHistory(
                profile_id=target_profile.id,
                slug=slug,
                display_name=name,
                created_by=user_uid,
                status="active"
            ))

    # 9. Update Additional Notes
    if has_health_field("additional_notes"):
        notes = get_health_field("additional_notes")
        if notes is not None:
            if not target_profile.additional_detail_rel:
                target_profile.additional_detail_rel = AdditionalDetail(profile_id=target_profile.id, created_by=user_uid)
                db.add(target_profile.additional_detail_rel)
            else:
                target_profile.additional_detail_rel.updated_at = func.now()
            target_profile.additional_detail_rel.additional_notes = notes

    # 10. Update Medications
    if has_health_field("current_medications"):
        db.query(Medication).filter(Medication.profile_id == target_profile.id).delete()
        meds = get_health_field("current_medications") or []
        for m in meds:
            db.add(Medication(
                profile_id=target_profile.id,
                name=m["name"],
                slug=m.get("slug"),
                dosage=m.get("dosage"),
                frequency=m.get("frequency"),
                timings=m.get("timings"),
                instructions=m.get("instructions"),
                food_relation=m.get("foodRelation"),
                tags=m.get("tags"),
                created_by=user_uid
            ))

    if not target_profile.email and not target_profile.phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one identity (email or phone number) must be present."
        )

    db.commit()
    db.refresh(target_profile)
    return target_profile



def get_user_by_identity(db: Session, identity: str) -> Optional[User]:
    """
    Check if a user exists by a given identity (either primary phone number/email on User, 
    or email/secondary phone number on Profile).
    Returns the User model if found, else None.
    """
    # 1. Check primary phone number or email in User
    user = db.query(User).filter(
        (User.phone_number == identity) | (User.email == identity)
    ).first()
    if user:
        return user
    
    # 2. Check email or phone number in Profile
    db_profile = db.query(Profile).filter(
        (Profile.email == identity) | (Profile.phone_number == identity)
    ).first()
    if db_profile:
        return db.query(User).filter(User.uid == db_profile.user_id).first()
        
    return None


def enable_user_biometrics(db: Session, user: User, device_id: str) -> UserDeviceBiometric:
    """Enables biometric login flags on User for a specific device and persists it."""
    from sqlalchemy.sql import func
    
    biometric = db.query(UserDeviceBiometric).filter(
        UserDeviceBiometric.user_id == user.uid,
        UserDeviceBiometric.device_id == device_id
    ).first()

    if biometric:
        biometric.is_enabled = True
        biometric.enabled_at = func.now()
        biometric.disabled_at = None
    else:
        biometric = UserDeviceBiometric(
            user_id=user.uid,
            device_id=device_id,
            is_enabled=True
        )
        db.add(biometric)

    db.commit()
    db.refresh(biometric)
    return biometric


def create_or_update_user_session(
    db: Session,
    user_uid: str,
    device_id: str,
    refresh_token: str,
    expires_at: datetime,
    device_model: Optional[str] = None,
    os_version: Optional[str] = None,
    platform: Optional[str] = None,
) -> UserSession:
    """Creates or updates a session for a user and a specific device ID."""
    # Find user first
    user = db.query(User).filter(User.uid == user_uid).first()
    if not user:
        raise ValueError(f"User with UID {user_uid} not found")

    session = db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.device_id == device_id
    ).first()

    if session:
        session.refresh_token = refresh_token
        session.expires_at = expires_at
        session.is_active = True
        if device_model:
            session.device_model = device_model
        if os_version:
            session.os_version = os_version
        if platform:
            session.platform = platform
    else:
        session = UserSession(
            user_id=user.id,
            device_id=device_id,
            device_model=device_model,
            os_version=os_version,
            platform=platform,
            refresh_token=refresh_token,
            expires_at=expires_at,
            is_active=True
        )
        db.add(session)

    db.commit()
    db.refresh(session)
    return session


def get_active_user_session(
    db: Session,
    user_uid: str,
    device_id: str,
    refresh_token: str
) -> Optional[UserSession]:
    """Retrieves an active session matching user UID, device ID and refresh token."""
    return db.query(UserSession).join(User).filter(
        User.uid == user_uid,
        UserSession.device_id == device_id,
        UserSession.refresh_token == refresh_token,
        UserSession.is_active == True
    ).first()


def invalidate_user_session(
    db: Session,
    user_uid: str,
    device_id: str
) -> Optional[UserSession]:
    """Marks a user's session as inactive for a specific device."""
    session = db.query(UserSession).join(User).filter(
        User.uid == user_uid,
        UserSession.device_id == device_id
    ).first()

    if session:
        session.is_active = False
        db.commit()
        db.refresh(session)
    return session


