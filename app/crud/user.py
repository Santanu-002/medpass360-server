from sqlalchemy import func
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
    FamilyHistory,
    Medication,
    Lifestyle,
    AdditionalDetail,
    ProfileMedicalSelection,
)
from app.schemas.user import ProfileUpdate


def get_user_by_id(db: Session, user_uid: str) -> Optional[User]:
    return db.query(User).filter(User.uid == user_uid).first()


def get_user_by_phone(db: Session, phone_number: str) -> Optional[User]:
    return db.query(User).filter(User.phone_number == phone_number).first()


def update_user_terms_agreement(db: Session, user_uid: str, is_agreed: bool = True) -> Optional[User]:
    user = get_user_by_id(db, user_uid)
    if user:
        user.is_agreed_to_terms = is_agreed
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


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
    if profile_update.relation != 'self':
        identity = profile_update.phone_number or profile_update.email
        if identity:
            care_user = get_user_by_identity(db, identity)
            if care_user:
                care_profile = db.query(Profile).filter(Profile.user_id == care_user.uid).first()
                if not care_profile or care_profile.created_by != user_uid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="A user with this phone number or email already exists."
                    )
            else:
                # Create a new user
                care_user = User(
                    phone_number=profile_update.phone_number,
                    email=profile_update.email
                )
                db.add(care_user)
                db.commit()
                db.refresh(care_user)
                care_profile = None

            if not care_profile:
                care_profile = Profile(
                    user_id=care_user.uid,
                    created_by=user_uid,
                    relation=profile_update.relation or "other",
                    is_verified=False
                )
                db.add(care_profile)
                db.commit()
                db.refresh(care_profile)
            else:
                care_profile.created_by = user_uid
                care_profile.relation = profile_update.relation or care_profile.relation or "other"
                db.add(care_profile)
                db.commit()
                db.refresh(care_profile)
            
            target_profile = care_profile
    else:
        db_profile.relation = "self"
        db_profile.created_by = user_uid

    # Check unique identity across all other users and profiles in the system
    email_to_check = profile_update.email
    phone_to_check = profile_update.phone_number

    if email_to_check:
        existing_email_user = db.query(User).filter(
            User.email == email_to_check,
            User.uid != target_profile.user_id
        ).first()
        existing_email_profile = db.query(Profile).filter(
            Profile.email == email_to_check,
            Profile.user_id != target_profile.user_id
        ).first()
        if existing_email_user or existing_email_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists."
            )

    if phone_to_check:
        existing_phone_user = db.query(User).filter(
            User.phone_number == phone_to_check,
            User.uid != target_profile.user_id
        ).first()
        existing_phone_profile = db.query(Profile).filter(
            Profile.phone_number == phone_to_check,
            Profile.user_id != target_profile.user_id
        ).first()
        if existing_phone_user or existing_phone_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this phone number already exists."
            )

    # 1. Update basic profile fields flatly for target_profile
    basic_fields = ["first_name", "last_name", "email", "phone_number", "date_of_birth", "gender", "avatar"]
    for key in basic_fields:
        if key in update_data:
            val = update_data[key]
            if key == "gender" and val is not None:
                val = val.value if hasattr(val, 'value') else val
            setattr(target_profile, key, val)

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
        db.query(ProfileMedicalSelection).filter(
            ProfileMedicalSelection.profile_id == target_profile.id,
            ProfileMedicalSelection.category.in_(["drug_allergy", "food_allergy", "environmental_allergy"])
        ).delete(synchronize_session=False)
        allergies_dict = get_health_field("allergies")
        if allergies_dict and isinstance(allergies_dict, dict):
            from app.core.utils import slugify
            for a_type in ["drug", "food", "environmental"]:
                items = allergies_dict.get(a_type, [])
                if items and isinstance(items, list):
                    category_name = f"{a_type}_allergy"
                    for item in items:
                        name = item["displayName"]
                        uid = item.get("uid")
                        slug = slugify(name)
                        
                        catalog_item = None
                        if uid:
                            catalog_item = db.query(Allergy).filter(Allergy.uid == uid).first()
                        
                        if not catalog_item:
                            catalog_item = db.query(Allergy).filter(
                                Allergy.slug == slug,
                                Allergy.allergy_type == a_type
                            ).first()
                            
                        if not catalog_item:
                            catalog_item = Allergy(
                                allergy_type=a_type,
                                slug=slug,
                                display_name=name,
                                created_by=user_uid,
                                status="active"
                            )
                            db.add(catalog_item)
                            db.flush()
                            
                        db.add(ProfileMedicalSelection(
                            profile_id=target_profile.id,
                            item_uid=catalog_item.uid,
                            category=category_name
                        ))

    # 5. Update Conditions (Chronic, Syndromes, Durations)
    if any(has_health_field(k) for k in ["chronic_conditions", "syndromes", "durations"]):
        db.query(ProfileMedicalSelection).filter(
            ProfileMedicalSelection.profile_id == target_profile.id,
            ProfileMedicalSelection.category.in_(["chronic_condition", "syndrome"])
        ).delete(synchronize_session=False)
        durations = get_health_field("durations") or {}
        from app.core.utils import slugify
        
        chronic = get_health_field("chronic_conditions") or []
        for item in chronic:
            name = item["displayName"]
            uid = item.get("uid")
            slug = slugify(name)
            dur = durations.get(name)
            
            catalog_item = None
            if uid:
                catalog_item = db.query(MedicalCondition).filter(MedicalCondition.uid == uid).first()
            if not catalog_item:
                catalog_item = db.query(MedicalCondition).filter(
                    MedicalCondition.slug == slug,
                    MedicalCondition.condition_type == "chronic"
                ).first()
            if not catalog_item:
                catalog_item = MedicalCondition(
                    condition_type="chronic",
                    slug=slug,
                    display_name=name,
                    created_by=user_uid,
                    status="active"
                )
                db.add(catalog_item)
                db.flush()
                
            db.add(ProfileMedicalSelection(
                profile_id=target_profile.id,
                item_uid=catalog_item.uid,
                category="chronic_condition",
                duration=dur
            ))
            
        syndromes = get_health_field("syndromes") or []
        for item in syndromes:
            name = item["displayName"]
            uid = item.get("uid")
            slug = slugify(name)
            dur = durations.get(name)
            
            catalog_item = None
            if uid:
                catalog_item = db.query(MedicalCondition).filter(MedicalCondition.uid == uid).first()
            if not catalog_item:
                catalog_item = db.query(MedicalCondition).filter(
                    MedicalCondition.slug == slug,
                    MedicalCondition.condition_type == "syndrome"
                ).first()
            if not catalog_item:
                catalog_item = MedicalCondition(
                    condition_type="syndrome",
                    slug=slug,
                    display_name=name,
                    created_by=user_uid,
                    status="active"
                )
                db.add(catalog_item)
                db.flush()
                
            db.add(ProfileMedicalSelection(
                profile_id=target_profile.id,
                item_uid=catalog_item.uid,
                category="syndrome",
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
        db.query(ProfileMedicalSelection).filter(
            ProfileMedicalSelection.profile_id == target_profile.id,
            ProfileMedicalSelection.category == "family_history"
        ).delete(synchronize_session=False)
        fam = get_health_field("family_history") or []
        from app.core.utils import slugify
        for item in fam:
            name = item["displayName"]
            uid = item.get("uid")
            slug = slugify(name)
            
            catalog_item = None
            if uid:
                catalog_item = db.query(FamilyHistory).filter(FamilyHistory.uid == uid).first()
            if not catalog_item:
                catalog_item = db.query(FamilyHistory).filter(
                    FamilyHistory.slug == slug
                ).first()
            if not catalog_item:
                catalog_item = FamilyHistory(
                    slug=slug,
                    display_name=name,
                    created_by=user_uid,
                    status="active"
                )
                db.add(catalog_item)
                db.flush()
                
            db.add(ProfileMedicalSelection(
                profile_id=target_profile.id,
                item_uid=catalog_item.uid,
                category="family_history"
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
            tags_list = m.get("tags") or []
            is_stopped_val = m.get("isStopped", False) or ("STOPPED" in tags_list)
            db.add(Medication(
                profile_id=target_profile.id,
                name=m["name"],
                slug=m.get("slug"),
                dosage=m.get("dosage"),
                frequency=m.get("frequency"),
                timings=m.get("timings"),
                instructions=m.get("instructions"),
                food_relation=m.get("foodRelation"),
                tags=tags_list,
                is_stopped=is_stopped_val,
                created_by=user_uid
            ))

    if target_profile.relation == "self":
        parent_user = db.query(User).filter(User.uid == user_uid).first()
        if parent_user:
            # Sync new values from update request to User table if provided
            if profile_update.email:
                parent_user.email = profile_update.email
            if profile_update.phone_number:
                parent_user.phone_number = profile_update.phone_number
                
            # If not in request but target_profile has it, sync as fallback
            if not target_profile.email and parent_user.email:
                target_profile.email = parent_user.email
            if not target_profile.phone_number and parent_user.phone_number:
                target_profile.phone_number = parent_user.phone_number

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


