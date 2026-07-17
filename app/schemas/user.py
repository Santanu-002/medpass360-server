from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, List
from datetime import date, datetime
from enum import Enum

# Helper config for camelCase aliases
class CamelModel(BaseModel):
    class Config:
        populate_by_name = True
        alias_generator = lambda string: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(string.split("_"))
        )


class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    PREFER_NOT_TO_SAY = "Prefer not to say"


class HeightUnit(str, Enum):
    CM = "cm"
    FT_IN = "ft-in"


class WeightUnit(str, Enum):
    KG = "kg"
    LBS = "lbs"


class HeightValue(CamelModel):
    value: str = Field(..., max_length=20)
    unit: HeightUnit


class WeightValue(CamelModel):
    value: str = Field(..., max_length=20)
    unit: WeightUnit


class VitalsUpdate(CamelModel):
    blood_type: Optional[str] = Field(None, max_length=10)
    height: Optional[HeightValue] = None
    weight: Optional[WeightValue] = None


class EmergencyContactUpdate(CamelModel):
    name: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=20)


class HealthProfileResponse(CamelModel):
    vitals: Optional[VitalsUpdate] = None
    emergency_contact: Optional[EmergencyContactUpdate] = None
    allergies: Optional[Dict[str, Any]] = None
    chronic_conditions: Optional[List[Dict[str, Any]]] = None
    syndromes: Optional[List[Dict[str, Any]]] = None
    durations: Optional[Dict[str, str]] = None
    lifestyle: Optional[Dict[str, Any]] = None
    recent_history: Optional[Dict[str, Any]] = None
    family_history: Optional[List[Dict[str, Any]]] = None
    additional_notes: Optional[str] = None
    current_medications: Optional[List[Dict[str, Any]]] = None


class ProfileBase(CamelModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, max_length=50)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    avatar: Optional[str] = Field(None, max_length=500)
    
    profile_target: Optional[str] = Field(None, max_length=50)
    care_person: Optional[Dict[str, Any]] = None
    
    created_by: Optional[str] = Field(None, max_length=36)
    relation: Optional[str] = Field("self", max_length=50)
    is_verified: bool = False


class ProfileCreate(ProfileBase):
    health_profile: Optional[HealthProfileResponse] = None


class ProfileUpdate(ProfileBase):
    health_profile: Optional[HealthProfileResponse] = None


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
    health_profile: Optional[HealthProfileResponse] = None

    class Config:
        from_attributes = True


class UserBase(CamelModel):
    phone_number: Optional[str] = Field(None, max_length=150)
    email: Optional[str] = Field(None, max_length=150)


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    uid: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    is_profile_completed: bool
    is_health_profile_completed: bool
    is_biometric_setup_completed: bool
    profiles: List[ProfileResponse] = []

    class Config:
        from_attributes = True
