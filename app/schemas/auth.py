from pydantic import BaseModel, Field

class SendOtpRequest(BaseModel):
    phone_number: str = Field(..., alias="phoneNumber")

    model_config = {
        "populate_by_name": True
    }
