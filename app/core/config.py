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

    # ─── OTP Settings ────────────────────────────────────────────
    OTP_MAX_REQUESTS: int = 4           # Max OTP sends per phone+device window
    OTP_RATE_LIMIT_TTL: int = 60        # Rate limit window in seconds (set to 3600 for prod)
    OTP_EXPIRY_TTL: int = 300           # OTP session validity in seconds (5 min)
    OTP_RESEND_DELAY_STEP: int = 30     # Resend delay increment per attempt (30s, 60s, 90s...)
    OTP_HASH_SALT: str = os.getenv("OTP_HASH_SALT", "medpass360_secure_salt_value")
    OTP_DEV_CODE: str = "123456"        # Hardcoded OTP code for dev/simulation

    # ─── JWT Token Settings ───────────────────────────────────────
    ACCESS_TOKEN_EXPIRY_SECONDS: int = 10 * 60       # 10 minutes
    REFRESH_TOKEN_EXPIRY_SECONDS: int = 7 * 24 * 60 * 60  # 7 days
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "medpass360_secure_jwt_secret_key_for_dev_only")
    JWT_ALGORITHM: str = "HS256"

settings = Settings()
