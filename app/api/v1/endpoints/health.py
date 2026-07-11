from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from redis_fastapi import AsyncRedisDep
import time

from app.api.deps import get_db
from app.schemas.response import ApiResponse

router = APIRouter()

@router.get("/", response_model=ApiResponse)
async def check_root():
    return ApiResponse(
        success=True,
        message="MedPass360 API is running (v1)",
        data={"timestamp": time.time()}
    )

@router.get("/health", response_model=ApiResponse)
async def health(
    db: Session = Depends(get_db),
    redis: AsyncRedisDep = None
):
    health_status = {
        "database": "unknown",
        "redis": "unknown"
    }
    
    # 1. Test database connection
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "healthy"
    except Exception as e:
        health_status["database"] = f"unhealthy: {str(e)}"
        
    # 2. Test Redis connection using SDK client
    try:
        if await redis.ping():
            health_status["redis"] = "healthy"
        else:
            health_status["redis"] = "unhealthy"
    except Exception as e:
        health_status["redis"] = f"unhealthy: {str(e)}"

    success = all(status == "healthy" for status in health_status.values())
    message = "Ping successful. Services are healthy." if success else "Ping completed with failures."
    
    return ApiResponse(
        success=success,
        message=message,
        data=health_status
    )

