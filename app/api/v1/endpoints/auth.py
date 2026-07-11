from fastapi import APIRouter
from redis_fastapi import AsyncRedisDep
import logging

from app.schemas.response import ApiResponse
from app.schemas.auth import SendOtpRequest

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/send-otp", response_model=ApiResponse)
async def send_otp(
    request: SendOtpRequest,
    redis: AsyncRedisDep = None
):
    # Simulated OTP code
    otp_code = "123456"
    
    # Save to Redis with a 5-minute expiration window if Redis is available
    if redis:
        try:
            await redis.setex(
                name=f"otp:{request.phone_number}",
                time=300,
                value=otp_code
            )
            logger.info(f"OTP {otp_code} saved in Redis for {request.phone_number}")
        except Exception as e:
            logger.error(f"Failed to save OTP to Redis: {str(e)}")

    # Visual console debug logs
    print(f"\n🔥 [SMS GATEWAY SIMULATION] Sent OTP: {otp_code} to {request.phone_number}\n")

    return ApiResponse(
        success=True,
        message=f"OTP sent successfully to {request.phone_number}.",
        data={"phoneNumber": request.phone_number}
    )
