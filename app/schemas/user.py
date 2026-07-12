from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any
from datetime import date, datetime


# Helper config for camelCase aliases
class CamelModel(BaseModel):
    class Config:
        populate_by_name = True
        alias_generator = lambda string: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(string.split("_"))
        )


from enum import Enum

class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    PREFER_NOT_TO_SAY = "Prefer not to say"


class ProfileBase(CamelModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, max_length=50)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    avatar: Optional[str] = Field(None, max_length=500)
    blood_type: Optional[str] = Field(None, max_length=10)
    allergies: Optional[Dict[str, Any]] = None
    medical_conditions: Optional[Dict[str, Any]] = None
    emergency_contact_name: Optional[str] = Field(None, max_length=150)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class RegisterRequest(CamelModel):
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    gender: Gender
    date_of_birth: date
    avatar: Optional[str] = Field(None, max_length=500)
    phone_number: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)


class ProfileResponse(ProfileBase):
    id: int
    uid: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserBase(CamelModel):
    phone_number: str = Field(..., max_length=150)


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    uid: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    profile: Optional[ProfileResponse] = None

    class Config:
        from_attributes = True
