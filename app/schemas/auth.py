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
