from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis_fastapi import AsyncRedisDep
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging
import hashlib
import time
import json
import jwt
from datetime import datetime, timezone

from app.core.config import settings
from app.core.utils import format_iso8601
from app.core.jwt_service import create_access_token, create_refresh_token, decode_token
from app.api.deps import get_db, get_current_user
from app.crud.user import get_or_create_user, update_profile
from app.models.user import User
from app.schemas.response import ApiResponse
from app.schemas.auth import SendOtpRequest, VerifyOtpRequest
from app.schemas.user import UserResponse, ProfileUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., alias="refreshToken")

    model_config = {
        "populate_by_name": True
    }


@router.post("/send-otp", response_model=ApiResponse)
async def send_otp(
    request: SendOtpRequest,
    req_raw: Request,
    redis: AsyncRedisDep = None
):
    device_id = req_raw.headers.get("x-device-id", "UnknownDevice")

    # 1. Fetch resend count history from Redis
    count = 0
    if redis:
        try:
            redis_key_count = f"otp_count:{request.phone_number}:{device_id}"
            count_bytes = await redis.get(redis_key_count)
            if count_bytes:
                count = int(count_bytes.decode())
        except Exception as e:
            logger.error(f"Failed to fetch OTP count from Redis: {str(e)}")

    # 2. Check if request limit is exceeded
    if count >= settings.OTP_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP request limit reached. Please try again later."
        )

    # 3. Increment request count
    if redis:
        try:
            redis_key_count = f"otp_count:{request.phone_number}:{device_id}"
            await redis.incr(redis_key_count)
            if count == 0:
                await redis.expire(redis_key_count, settings.OTP_RATE_LIMIT_TTL)
        except Exception as e:
            logger.error(f"Failed to increment OTP count in Redis: {str(e)}")

    # 4. Calculate timing details
    current_time = int(time.time())
    expiry_time = current_time + settings.OTP_EXPIRY_TTL

    delay_seconds = (count + 1) * settings.OTP_RESEND_DELAY_STEP
    resendable_dt = datetime.fromtimestamp(current_time + delay_seconds, tz=timezone.utc)
    resendable_at = format_iso8601(resendable_dt)

    # 5. Generate secure otpId as a salted hash of the payload
    payload_str = f"{request.phone_number}:{device_id}:{expiry_time}:{settings.OTP_HASH_SALT}"
    otp_id = hashlib.sha256(payload_str.encode()).hexdigest()

    # 6. Save OTP session to Redis for verification
    otp_code = settings.OTP_DEV_CODE
    if redis:
        try:
            redis_key_otp = f"otp_session:{otp_id}"
            session_data = {
                "phoneNumber": request.phone_number,
                "deviceId": device_id,
                "otp": otp_code,
                "expiryTime": expiry_time
            }
            await redis.setex(
                name=redis_key_otp,
                time=settings.OTP_EXPIRY_TTL,
                value=json.dumps(session_data)
            )
            logger.info(f"Saved OTP session {otp_id} to Redis")
        except Exception as e:
            logger.error(f"Failed to save OTP session to Redis: {str(e)}")

    # Console simulation logs
    print(f"\n========================================")
    print(f"🔥 [SMS GATEWAY SIMULATION] Sent OTP: {otp_code} to {request.phone_number}")
    print(f"Session OTP ID: {otp_id}")
    print(f"Resend delay: {delay_seconds}s (resendable at timestamp: {resendable_at})")
    print(f"========================================\n")

    return ApiResponse(
        success=True,
        message="OTP sent successfully.",
        data={
            "phone": request.phone_number,
            "otpId": otp_id,
            "resendableAt": resendable_at
        }
    )


@router.post("/verify-otp", response_model=ApiResponse)
async def verify_otp(
    request: VerifyOtpRequest,
    redis: AsyncRedisDep = None,
    db: Session = Depends(get_db)
):
    if not redis:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Redis storage is not configured."
        )

    redis_key_otp = f"otp_session:{request.otp_id}"
    session_bytes = await redis.get(redis_key_otp)
    if not session_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code expired. Please request a new one."
        )

    session_data = json.loads(session_bytes.decode())

    # Any OTP code other than "111111" is valid for now
    if request.code == "111111":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code."
        )

    # Cleanup OTP session on successful verification
    await redis.delete(redis_key_otp)

    # 1. Fetch or create actual user in the PostgreSQL DB
    db_user = get_or_create_user(db, phone_number=session_data["phoneNumber"])

    # 2. Generate auth tokens with real user ID
    access = create_access_token(subject=db_user.id)
    refresh = create_refresh_token(subject=db_user.id)

    # 3. Construct user details response
    user_resp = UserResponse.model_validate(db_user)

    token_data = {
        "accessToken": access["token"],
        "refreshToken": refresh["token"],
        "accessTokenExpiry": access["expiresAt"],
        "refreshTokenExpiry": refresh["expiresAt"],
        "issuedAt": access["issuedAt"]
    }

    return ApiResponse(
        success=True,
        message="Verification successful.",
        data={
            "user": user_resp,
            "token": token_data,
        }
    )


@router.post("/refresh", response_model=ApiResponse)
async def refresh_tokens(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    try:
        payload = decode_token(request.refresh_token)
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials/token expired"
        )

    # Generate new access and refresh tokens
    access = create_access_token(subject=user_id)
    refresh = create_refresh_token(subject=user_id)

    token_data = {
        "accessToken": access["token"],
        "refreshToken": refresh["token"],
        "accessTokenExpiry": access["expiresAt"],
        "refreshTokenExpiry": refresh["expiresAt"],
        "issuedAt": access["issuedAt"]
    }

    return ApiResponse(
        success=True,
        message="Token refresh successful.",
        data={
            "token": token_data
        }
    )


@router.get("/profile", response_model=ApiResponse[UserResponse])
def get_profile(
    current_user: User = Depends(get_current_user)
):
    user_resp = UserResponse.model_validate(current_user)
    return ApiResponse(
        success=True,
        message="Profile retrieved successfully.",
        data=user_resp
    )


@router.put("/profile", response_model=ApiResponse[UserResponse])
def update_user_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    update_profile(db, user_id=current_user.id, profile_update=profile_data)
    
    # Refresh user object from DB to get updated profile relation
    db.refresh(current_user)
    user_resp = UserResponse.model_validate(current_user)
    
    return ApiResponse(
        success=True,
        message="Profile updated successfully.",
        data=user_resp
    )


@router.post("/logout", response_model=ApiResponse)
async def logout(
    current_user: User = Depends(get_current_user)
):
    # In a real environment, we would blacklist the token in Redis.
    # For now, return a successful response.
    return ApiResponse(
        success=True,
        message="Logout successful."
    )
