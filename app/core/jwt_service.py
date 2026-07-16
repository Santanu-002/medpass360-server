import jwt
import time
import uuid
from datetime import datetime, timezone
from app.core.config import settings
from app.core.utils import format_iso8601


def _build_token(subject: str, token_type: str, ttl_seconds: int) -> dict:
    """Generate a signed JWT and return token + metadata."""
    issued_at = int(time.time())
    expiry = issued_at + ttl_seconds

    payload = {
        "sub": subject,
        "type": token_type,
        "iat": issued_at,
        "exp": expiry,
        "jti": str(uuid.uuid4()),
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return {
        "token": token,
        "issuedAt": format_iso8601(datetime.fromtimestamp(issued_at, tz=timezone.utc)),
        "expiresAt": format_iso8601(datetime.fromtimestamp(expiry, tz=timezone.utc)),
    }


def create_access_token(subject: str) -> dict:
    return _build_token(subject, "access", settings.ACCESS_TOKEN_EXPIRY_SECONDS)


def create_refresh_token(subject: str) -> dict:
    return _build_token(subject, "refresh", settings.REFRESH_TOKEN_EXPIRY_SECONDS)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises jwt.PyJWTError on failure."""
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )

