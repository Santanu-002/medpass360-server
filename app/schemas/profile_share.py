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
            # SQLAlchemy model instance
            token = getattr(data, "token", "")
            expires_at = getattr(data, "expires_at", None)
            max_uses = getattr(data, "max_uses", None)
        else:
            token = data.get("token", "")
            expires_at = data.get("expires_at", None)
            max_uses = data.get("max_uses", None)

        expires_at_str = expires_at.isoformat() if isinstance(expires_at, datetime) else str(expires_at)
        
        # Format the JSON string that will be encoded into the QR code
        qr_data = {
            "type": "share",
            "token": token,
            "expiresAt": expires_at_str,
            "maxUses": max_uses
        }
        
        # Serialize to a compact JSON string
        qr_json_str = json.dumps(qr_data)
        
        if not isinstance(data, dict):
            data.qr_value = qr_json_str
        else:
            data["qr_value"] = qr_json_str
            
        return data

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
