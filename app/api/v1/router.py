from fastapi import APIRouter
from app.api.v1.endpoints import health, auth

api_router = APIRouter()

# Include endpoints routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
