import os
from datetime import date
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.profile import Profile
from app.crud import user as crud_user
from app.schemas.user import Gender

def validate_registration_data(
    first_name: str,
    last_name: str,
    gender: Gender,
    date_of_birth_str: str
) -> date:
    first_name = first_name.strip()
    last_name = last_name.strip()

    if not first_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="First name cannot be empty."
        )
    if not last_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last name cannot be empty."
        )

    try:
        dob = date.fromisoformat(date_of_birth_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dateOfBirth format. Use YYYY-MM-DD."
        )

    if dob > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date of birth cannot be in the future."
        )

    return dob

async def register_user_profile(
    db: Session,
    current_user: User,
    first_name: str,
    last_name: str,
    gender: Gender,
    date_of_birth_str: str,
    avatar_url: Optional[str] = None,
    phone_number: Optional[str] = None,
    email: Optional[str] = None
) -> User:
    # 1. Check if profile already exists
    if current_user.profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile already exists."
        )

    # 2. Validate inputs
    dob = validate_registration_data(first_name, last_name, gender, date_of_birth_str)

    # Determine type of login:
    is_email_login = "@" in current_user.phone_number
    
    if is_email_login:
        if not phone_number or not phone_number.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is required."
            )
        final_phone = phone_number.strip()
        final_email = current_user.phone_number
    else:
        final_phone = current_user.phone_number
        final_email = email.strip() if email and email.strip() else None

    # Check for conflicts
    if final_phone:
        user_by_phone = db.query(User).filter(User.phone_number == final_phone).first()
        if user_by_phone and user_by_phone.uid != current_user.uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is already in use by another account."
            )

    if final_email:
        user_by_email = db.query(User).filter(User.email == final_email).first()
        if user_by_email and user_by_email.uid != current_user.uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already in use by another account."
            )

    # Sync resolved identities back to the User model
    if final_phone:
        current_user.phone_number = final_phone
    if final_email:
        current_user.email = final_email
    db.add(current_user)
    db.flush()

    # 3. Create profile (avatar_url is already a URL string from /media/upload)
    crud_user.create_profile(
        db=db,
        user_uid=current_user.uid,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        gender=gender.value,
        date_of_birth=dob,
        avatar=avatar_url
    )
    
    # Refresh user to load profile relationship
    db.refresh(current_user)
    return current_user
