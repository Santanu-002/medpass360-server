from pydantic import BaseModel, Field

class SendOtpRequest(BaseModel):
    phone_number: str = Field(..., alias="phoneNumber")

    model_config = {
        "populate_by_name": True
    }

class VerifyOtpRequest(BaseModel):
    otp_id: str = Field(..., alias="otpId")
    code: str = Field(..., alias="code")

    model_config = {
        "populate_by_name": True
    }

class TokenResponse(BaseModel):
    access_token: str = Field(..., alias="accessToken")
    refresh_token: str = Field(..., alias="refreshToken")
    access_token_expiry: str = Field(..., alias="accessTokenExpiry")
    refresh_token_expiry: str = Field(..., alias="refreshTokenExpiry")
    issued_at: str = Field(..., alias="issuedAt")

    model_config = {
        "populate_by_name": True
    }
