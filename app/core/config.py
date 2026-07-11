import os

class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:postgrespassword@localhost:5432/medpass360"
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    ENV: str = os.getenv("ENV", "development")
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "MedPass360"

settings = Settings()
