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


class ProfileBase(CamelModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=50)
    blood_type: Optional[str] = Field(None, max_length=10)
    allergies: Optional[Dict[str, Any]] = None
    medical_conditions: Optional[Dict[str, Any]] = None
    emergency_contact_name: Optional[str] = Field(None, max_length=150)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserBase(CamelModel):
    phone_number: str = Field(..., max_length=20)


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    profile: Optional[ProfileResponse] = None

    class Config:
        from_attributes = True
