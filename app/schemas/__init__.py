# Schemas package initialization
from app.schemas.response import ApiResponse
from app.schemas.auth import SendOtpRequest, VerifyOtpRequest, TokenResponse
from app.schemas.user import UserResponse, ProfileResponse, ProfileUpdate
from app.schemas.medical_option import MedicalOptionResponse, GroupedMedicalOptionsResponse

__all__ = [
    "ApiResponse", 
    "SendOtpRequest", 
    "VerifyOtpRequest", 
    "TokenResponse", 
    "UserResponse", 
    "ProfileResponse", 
    "ProfileUpdate",
    "MedicalOptionResponse",
    "GroupedMedicalOptionsResponse"
]
