from fastapi import APIRouter, Depends, HTTPException, Request
from redis_fastapi import AsyncRedisDep
import logging
import hashlib
import time
import json

from app.schemas.response import ApiResponse
from app.schemas.auth import SendOtpRequest

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

    # 2. Check if request limit is exceeded (maximum 4 requests)
    if count >= 4:
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
                # Expire rate limit state after 1 hour
                await redis.expire(redis_key_count, 3600)
        except Exception as e:
            logger.error(f"Failed to increment OTP count in Redis: {str(e)}")

    # 4. Calculate timing details
    current_time = int(time.time())
    expiry_time = current_time + 300  # OTP valid for 5 minutes
    
    # Delay: 0th request -> 30s, 1st -> 60s, 2nd -> 90s, 3rd -> 120s
    delay_seconds = (count + 1) * 30
    resendable_at = current_time + delay_seconds

    # 5. Generate secure otpId as a salted hash of the payload
    salt = "medpass360_secure_salt_value"
    payload_str = f"{request.phone_number}:{device_id}:{expiry_time}:{salt}"
    otp_id = hashlib.sha256(payload_str.encode()).hexdigest()

    # 6. Save OTP session to Redis for verification
    otp_code = "123456"
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
                time=300,
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
            "otpId": otp_id,
            "resendableAt": resendable_at
        }
    )
