from fastapi import APIRouter, Depends, HTTPException, Request
from redis_fastapi import AsyncRedisDep
import logging
import hashlib
import time
import json
from datetime import datetime, timezone
from app.core.config import settings
from app.core.utils import format_iso8601

from app.schemas.response import ApiResponse
from app.schemas.auth import SendOtpRequest, VerifyOtpRequest

logger = logging.getLogger(__name__)
router = APIRouter()

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
            status_code=400,
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
    redis: AsyncRedisDep = None
):
    if not redis:
        raise HTTPException(
            status_code=500,
            detail="Redis storage is not configured."
        )

    redis_key_otp = f"otp_session:{request.otp_id}"
    session_bytes = await redis.get(redis_key_otp)
    if not session_bytes:
        raise HTTPException(
            status_code=400,
            detail="Verification code expired. Please request a new one."
        )

    session_data = json.loads(session_bytes.decode())

    # Any OTP code other than "111111" is valid for now
    if request.code == "111111":
        raise HTTPException(
            status_code=400,
            detail="Invalid verification code."
        )

    # Cleanup OTP session on successful verification
    await redis.delete(redis_key_otp)

    return ApiResponse(
        success=True,
        message="Verification successful.",
        data={
            "user": {
                "id": "mock-user-uuid",
                "phoneNumber": session_data["phoneNumber"]
            }
        }
    )
