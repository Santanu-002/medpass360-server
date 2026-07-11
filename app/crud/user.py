from sqlalchemy.orm import Session
from typing import Optional
from app.models.user import User
from app.models.profile import Profile
from app.schemas.user import ProfileUpdate


def get_user_by_id(db: Session, user_uid: str) -> Optional[User]:
    return db.query(User).filter(User.uid == user_uid).first()


def get_user_by_phone(db: Session, phone_number: str) -> Optional[User]:
    return db.query(User).filter(User.phone_number == phone_number).first()


def create_user(db: Session, phone_number: str) -> User:
    # Create the user
    db_user = User(phone_number=phone_number)
    db.add(db_user)
    db.flush()  # Populates user uid and id

    # Create associated empty profile linked by user_id -> users.uid
    db_profile = Profile(user_id=db_user.uid)
    db.add(db_profile)
    
    db.commit()
    db.refresh(db_user)
    return db_user


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

    # Exclude unset fields from the update dict
    update_data = profile_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_profile, key, value)

    db.commit()
    db.refresh(db_profile)
    return db_profile
