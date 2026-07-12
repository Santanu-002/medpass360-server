import os
from datetime import date
from typing import Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.profile import Profile
from app.crud import user as crud_user
from app.schemas.user import Gender

# Root upload path
UPLOAD_DIR = "/workspace/uploads/avatars"

def validate_registration_data(
    first_name: str,
    last_name: str,
    gender: Gender,
    date_of_birth_str: str
) -> date:
    # Trim inputs
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

async def save_avatar_file(user_uid: str, avatar: UploadFile) -> str:
    if not avatar.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid avatar file."
        )
    
    # Create target directories
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Save the file
    file_ext = os.path.splitext(avatar.filename)[1] or ".jpg"
    file_name = f"{user_uid}_avatar{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    
    try:
        content = await avatar.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save profile picture: {str(e)}"
        )
        
    return f"/uploads/avatars/{file_name}"

async def register_user_profile(
    db: Session,
    current_user: User,
    first_name: str,
    last_name: str,
    gender: Gender,
    date_of_birth_str: str,
    avatar: Optional[UploadFile] = None,
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
        # Email login: phone_number is required and cannot be empty
        if not phone_number or not phone_number.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is required."
            )
        final_phone = phone_number.strip()
        final_email = current_user.phone_number  # prefilled from login identity
    else:
        # Phone login: email is optional
        final_phone = current_user.phone_number  # prefilled from login identity
        final_email = email.strip() if email and email.strip() else None

    # Check for email or phone number conflicts with other users/profiles
    if final_phone:
        user_by_phone = db.query(User).filter(User.phone_number == final_phone).first()
        if user_by_phone and user_by_phone.uid != current_user.uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is already in use by another account."
            )
        profile_by_phone = db.query(Profile).filter(Profile.phone_number == final_phone).first()
        if profile_by_phone and profile_by_phone.user_id != current_user.uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is already in use by another account."
            )

    if final_email:
        user_by_email = db.query(User).filter(User.phone_number == final_email).first()
        if user_by_email and user_by_email.uid != current_user.uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already in use by another account."
            )
        profile_by_email = db.query(Profile).filter(Profile.email == final_email).first()
        if profile_by_email and profile_by_email.user_id != current_user.uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already in use by another account."
            )

    # 3. Save avatar if provided
    avatar_url = None
    if avatar and avatar.filename:
        avatar_url = await save_avatar_file(current_user.uid, avatar)

    # 4. Create profile
    crud_user.create_profile(
        db=db,
        user_uid=current_user.uid,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        gender=gender.value,
        date_of_birth=dob,
        avatar=avatar_url,
        phone_number=final_phone,
        email=final_email
    )
    
    # Refresh user to load profile relationship
    db.refresh(current_user)
    return current_user
