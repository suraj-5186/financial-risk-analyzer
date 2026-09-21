import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Financial Behavior and Risk Analyzer"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkeyforfinancialriskanalyzer1234567890!")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:////tmp/financial_risk.db" if os.getenv("VERCEL") else "sqlite:///./financial_risk.db")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Email / SMTP configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@finrisk.ai")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    # Frontend URL for link construction
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

    # Password reset expiration in minutes
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30"))

    # Avatar Storage Configuration
    AVATAR_STORAGE_BACKEND: str = os.getenv("AVATAR_STORAGE_BACKEND", "local")
    S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "")
    S3_ACCESS_KEY_ID: str = os.getenv("S3_ACCESS_KEY_ID", "")
    S3_SECRET_ACCESS_KEY: str = os.getenv("S3_SECRET_ACCESS_KEY", "")
    S3_REGION: str = os.getenv("S3_REGION", "auto")
    S3_PUBLIC_BASE_URL: str = os.getenv("S3_PUBLIC_BASE_URL", "").rstrip("/")
    # Bank Synchronization Configuration (Task 19)
    BANK_SYNC_PROVIDER: str = os.getenv("BANK_SYNC_PROVIDER", "mock")
    BANK_SYNC_ENABLED: bool = os.getenv("BANK_SYNC_ENABLED", "true").lower() in ("true", "1", "yes")
    BANK_TOKEN_ENCRYPTION_KEY: str = os.getenv("BANK_TOKEN_ENCRYPTION_KEY", "")
    PLAID_CLIENT_ID: str = os.getenv("PLAID_CLIENT_ID", "")
    PLAID_SECRET: str = os.getenv("PLAID_SECRET", "")
    PLAID_ENV: str = os.getenv("PLAID_ENV", "sandbox")

    # Environment and CORS Configuration
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "")

    @property
    def is_production(self) -> bool:
        return (
            self.ENVIRONMENT.lower() in ("production", "prod")
            or bool(os.getenv("RENDER"))
        )

    class Config:
        case_sensitive = True

settings = Settings()

import logging

logger = logging.getLogger(__name__)

DEFAULT_DEV_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

def resolve_cors_origins(
    raw_origins: str | None = None,
    is_production: bool | None = None,
) -> tuple[list[str], bool]:
    """
    Resolves and sanitizes CORS allowed origins and credentials behavior.

    Security Rules:
    1. Production NEVER falls back to wildcard (*). If ALLOWED_ORIGINS is missing or empty in production,
       all cross-origin CORS requests are blocked (empty list, allow_credentials=False).
    2. In development (non-production), if ALLOWED_ORIGINS is missing or empty, default localhost
       development origins are allowed with credentials enabled for convenience.
    3. Credentials (allow_credentials=True) are NEVER combined with wildcard origins (*).
    4. If raw_origins contains valid origins, whitespace and trailing slashes are trimmed,
       missing schemes default to https://, and duplicates are removed.
    """
    if raw_origins is None:
        raw_origins = os.getenv("ALLOWED_ORIGINS", settings.ALLOWED_ORIGINS)

    if is_production is None:
        is_production = settings.is_production

    tokens = [t.strip() for t in raw_origins.split(",") if t.strip()]
    origins: list[str] = []

    for token in tokens:
        if token == "*":
            if "*" not in origins:
                origins.append("*")
            continue
        cleaned = token.rstrip("/")
        if not cleaned:
            continue
        if not cleaned.startswith(("http://", "https://")):
            cleaned = f"https://{cleaned}"
        if cleaned not in origins:
            origins.append(cleaned)

    # Rule 3: Credentials are never combined with wildcard origins
    if "*" in origins:
        if is_production:
            logger.warning("CORS: Wildcard origin ('*') explicitly configured in production. Credentials disabled.")
        return ["*"], False

    # Configured origins provided
    if origins:
        return origins, True

    # Rule 1: Production must NOT fall back to wildcard origins
    if is_production:
        logger.warning(
            "CORS: Production environment detected with missing or empty ALLOWED_ORIGINS. "
            "All cross-origin CORS requests are blocked until ALLOWED_ORIGINS is configured."
        )
        return [], False

    # Rule 2: Convenient local development fallback
    logger.info(
        "CORS: Development environment detected without ALLOWED_ORIGINS. "
        "Allowing default localhost origins with credentials."
    )
    return list(DEFAULT_DEV_ORIGINS), True
