from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis_fastapi import FastAPIRedis
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.middleware import DeviceHeaderMiddleware
from app.api.v1.router import api_router
from app.api.v1.endpoints import health

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-Ready FastAPI Backend with PostgreSQL, Redis and clean architecture",
    version="1.0.0"
)

# Initialize Redis connection pool lifecycle & caching dependencies via SDK
FastAPIRedis(app).lifespan().caching()

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(DeviceHeaderMiddleware)

# Register consistent error exception handlers
register_exception_handlers(app)

@app.on_event("startup")
def startup_event():
    from app.core.database import Base, engine
    import app.models
    Base.metadata.create_all(bind=engine)


# Mount API routers
# Mount health endpoints at root level for easy server monitoring/pings
app.include_router(health.router)

# Mount versioned API routes
app.include_router(api_router, prefix=settings.API_V1_STR)
