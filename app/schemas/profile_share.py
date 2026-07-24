import json
from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime
from app.schemas.user import CamelModel

class ProfileShareCreate(CamelModel):
    max_uses: Optional[int] = None
    expires_in_days: int = 7

class ProfileShareResponse(CamelModel):
    id: int
    profile_id: int
    created_by: str
    token: str
    expires_at: datetime
    max_uses: Optional[int] = None
    uses_count: int
    is_active: bool
    qr_value: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_qr_value(cls, data):
        # Allow dict input or SQLAlchemy object input
        if not isinstance(data, dict):
            token = getattr(data, "token", "")
        else:
            token = data.get("token", "")

        # Format the sharing website URL containing the token code
        qr_url = f"https://medpass360.com/profile/shared?code={token}"
        
        if not isinstance(data, dict):
            data.qr_value = qr_url
        else:
            data["qr_value"] = qr_url
            
        return data

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
