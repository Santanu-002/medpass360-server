from fastapi import APIRouter, Depends, HTTPException, Request, status, Form, File, UploadFile
from typing import Optional
from redis_fastapi import AsyncRedisDep
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging
import hashlib
import time
import json
import jwt
import os
import shutil
from datetime import datetime, timezone, date

from app.core.config import settings
from app.core.utils import format_iso8601
from app.core.jwt_service import create_access_token, create_refresh_token, decode_token
from app.api.deps import get_db, get_current_user
from app.crud.user import (
    get_or_create_user,
    update_profile,
    create_profile,
    get_user_by_identity,
    enable_user_biometrics,
    create_or_update_user_session,
    get_active_user_session,
    invalidate_user_session
)
from app.models.user import User
from app.schemas.response import ApiResponse
from app.schemas.auth import SendOtpRequest, VerifyOtpRequest
from app.schemas.user import UserResponse, ProfileUpdate, RegisterRequest

logger = logging.getLogger(__name__)
router = APIRouter()


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., alias="refreshToken")

    model_config = {
        "populate_by_name": True
    }


@router.post("/create-account", response_model=ApiResponse)
async def create_account(
    request: SendOtpRequest,
    req_raw: Request,
    redis: AsyncRedisDep = None,
    db: Session = Depends(get_db)
):
    # Enforce that user does not exist
    user = get_user_by_identity(db, request.identity)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account already exists with this phone number or email. Please login."
        )

    device_id = req_raw.headers.get("x-device-id", "UnknownDevice")

    # 1. Fetch resend count history from Redis
    count = 0
    if redis:
        try:
            redis_key_count = f"otp_count:{request.identity}:{device_id}"
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
            redis_key_count = f"otp_count:{request.identity}:{device_id}"
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
    payload_str = f"{request.identity}:{device_id}:{expiry_time}:{settings.OTP_HASH_SALT}"
    otp_id = hashlib.sha256(payload_str.encode()).hexdigest()

    # 6. Save OTP session to Redis for verification
    otp_code = settings.OTP_DEV_CODE
    if redis:
        try:
            redis_key_otp = f"otp_session:{otp_id}"
            session_data = {
                "phoneNumber": request.identity,
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
    print(f"🔥 [SMS/EMAIL GATEWAY SIMULATION] Sent OTP: {otp_code} to {request.identity} via {request.type}")
    print(f"Session OTP ID: {otp_id}")
    print(f"Resend delay: {delay_seconds}s (resendable at timestamp: {resendable_at})")
    print(f"========================================\n")

    return ApiResponse(
        success=True,
        message="OTP sent successfully.",
        data={
            "identity": request.identity,
            "otpId": otp_id,
            "resendableAt": resendable_at
        }
    )


@router.post("/verify-otp", response_model=ApiResponse)
async def verify_otp(
    request: VerifyOtpRequest,
    req_raw: Request,
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

    # 2. Generate auth tokens with real user ID (uid)
    access = create_access_token(subject=db_user.uid)
    refresh = create_refresh_token(subject=db_user.uid)

    # 3. Create or update session for this device
    device_id = req_raw.headers.get("x-device-id", "UnknownDevice")
    device_name = req_raw.headers.get("x-device-name")
    device_model = req_raw.headers.get("x-device-model")
    os_version = req_raw.headers.get("x-os-version")
    platform = req_raw.headers.get("x-platform")
    expires_at = datetime.fromisoformat(refresh["expiresAt"].replace("Z", "+00:00"))

    create_or_update_user_session(
        db=db,
        user_uid=db_user.uid,
        device_id=device_id,
        refresh_token=refresh["token"],
        expires_at=expires_at,
        device_name=device_name,
        device_model=device_model,
        os_version=os_version,
        platform=platform,
    )

    # 4. Construct user details response
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
    req_raw: Request,
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

    device_id = req_raw.headers.get("x-device-id", "UnknownDevice")

    # Fetch active user session matching this device and refresh token
    session = get_active_user_session(
        db=db,
        user_uid=user_id,
        device_id=device_id,
        refresh_token=request.refresh_token
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Active session not found or token invalidated"
        )

    # Check expiration
    if session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        session.is_active = False
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired"
        )

    # Generate new access and refresh tokens
    access = create_access_token(subject=user_id)
    refresh = create_refresh_token(subject=user_id)
    expires_at = datetime.fromisoformat(refresh["expiresAt"].replace("Z", "+00:00"))

    # Update existing session row (do NOT insert update using device-id)
    device_name = req_raw.headers.get("x-device-name")
    device_model = req_raw.headers.get("x-device-model")
    os_version = req_raw.headers.get("x-os-version")
    platform = req_raw.headers.get("x-platform")

    create_or_update_user_session(
        db=db,
        user_uid=user_id,
        device_id=device_id,
        refresh_token=refresh["token"],
        expires_at=expires_at,
        device_name=device_name,
        device_model=device_model,
        os_version=os_version,
        platform=platform,
    )

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


@router.post("/logout", response_model=ApiResponse)
async def logout(
    req_raw: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    device_id = req_raw.headers.get("x-device-id", "UnknownDevice")
    invalidate_user_session(db=db, user_uid=current_user.uid, device_id=device_id)

    return ApiResponse(
        success=True,
        message="Logout successful."
    )


@router.get("/check-exists", response_model=ApiResponse)
async def check_exists(
    identity: str,
    db: Session = Depends(get_db)
):
    user = get_user_by_identity(db, identity)
    return ApiResponse(
        success=True,
        message="Checked identity existence successfully.",
        data={
            "exists": user is not None,
            "hasBiometrics": user.has_biometrics if user else False
        }
    )


class BiometricLoginRequest(BaseModel):
    identity: str


@router.post("/enable-biometrics", response_model=ApiResponse)
async def enable_biometrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    enable_user_biometrics(db, current_user)
    return ApiResponse(
        success=True,
        message="Biometrics enabled successfully."
    )


@router.post("/login/otp", response_model=ApiResponse)
async def login_otp(
    request: SendOtpRequest,
    req_raw: Request,
    redis: AsyncRedisDep = None,
    db: Session = Depends(get_db)
):
    # Enforce that user exists
    user = get_user_by_identity(db, request.identity)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this phone number or email. Please create an account."
        )

    device_id = req_raw.headers.get("x-device-id", "UnknownDevice")

    # Fetch resend count history from Redis
    count = 0
    if redis:
        try:
            redis_key_count = f"otp_count:{request.identity}:{device_id}"
            count_bytes = await redis.get(redis_key_count)
            if count_bytes:
                count = int(count_bytes.decode())
        except Exception as e:
            logger.error(f"Failed to fetch OTP count from Redis: {str(e)}")

    # Check if request limit is exceeded
    if count >= settings.OTP_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP request limit reached. Please try again later."
        )

    # Increment request count
    if redis:
        try:
            redis_key_count = f"otp_count:{request.identity}:{device_id}"
            await redis.incr(redis_key_count)
            if count == 0:
                await redis.expire(redis_key_count, settings.OTP_RATE_LIMIT_TTL)
        except Exception as e:
            logger.error(f"Failed to increment OTP count in Redis: {str(e)}")

    current_time = int(time.time())
    expiry_time = current_time + settings.OTP_EXPIRY_TTL

    delay_seconds = (count + 1) * settings.OTP_RESEND_DELAY_STEP
    resendable_dt = datetime.fromtimestamp(current_time + delay_seconds, tz=timezone.utc)
    resendable_at = format_iso8601(resendable_dt)

    # Generate secure otpId as a salted hash of the payload
    payload_str = f"{request.identity}:{device_id}:{expiry_time}:{settings.OTP_HASH_SALT}"
    otp_id = hashlib.sha256(payload_str.encode()).hexdigest()

    # Save OTP session to Redis for verification
    otp_code = settings.OTP_DEV_CODE
    if redis:
        try:
            redis_key_otp = f"otp_session:{otp_id}"
            session_data = {
                "phoneNumber": request.identity,
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
    print(f"🔥 [SMS/EMAIL GATEWAY SIMULATION] Sent Login OTP: {otp_code} to {request.identity} via {request.type}")
    print(f"Session OTP ID: {otp_id}")
    print(f"Resend delay: {delay_seconds}s (resendable at timestamp: {resendable_at})")
    print(f"========================================\n")

    return ApiResponse(
        success=True,
        message="OTP sent successfully.",
        data={
            "identity": request.identity,
            "otpId": otp_id,
            "resendableAt": resendable_at
        }
    )


@router.post("/login", response_model=ApiResponse)
async def login(
    request: BiometricLoginRequest,
    db: Session = Depends(get_db)
):
    db_user = get_user_by_identity(db, request.identity)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    if not db_user.has_biometrics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Biometric authentication is not enabled for this user."
        )

    access = create_access_token(subject=db_user.uid)
    refresh = create_refresh_token(subject=db_user.uid)
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
        message="Biometric login successful.",
        data={
            "user": user_resp,
            "token": token_data,
        }
    )
