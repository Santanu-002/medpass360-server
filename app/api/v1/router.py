from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, registration, medical_option, media, health_profile

api_router = APIRouter()

# Include endpoints routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(registration.router, prefix="/auth", tags=["registration"])
api_router.include_router(medical_option.router, tags=["medical-options"])
api_router.include_router(media.router, prefix="/media", tags=["media"])
api_router.include_router(health_profile.router, tags=["health-profile"])

