"""
Centralized configuration for the ClearFlow Small Chits backend.
All secrets are loaded from environment variables (.env) — nothing is hardcoded,
per the Master Blueprint's "zero hardcoded values" mandate for the math engine
and "Day 1 security" mandate for OAuth.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "ClearFlow Small Chits API"
    ENV: str = "production"
    SECRET_KEY: str  # used to sign session/JWT cookies
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    # --- Google OAuth 2.0 (Day 1 auth mandate) ---
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    GOOGLE_DRIVE_SCOPE: str = "https://www.googleapis.com/auth/drive.file"

    # --- NocoDB (single source of truth — connect to your own instance) ---
    NOCODB_BASE_URL: str  # e.g. https://nocodb.yourdomain.com
    NOCODB_API_TOKEN: str
    NOCODB_BASE_ID: str  # NocoDB "base" (project) id
    NOCODB_TABLE_MANAGERS: str = "Managers"
    NOCODB_TABLE_CHITTIS: str = "Chittis"
    NOCODB_TABLE_SHARES: str = "Shares"
    NOCODB_TABLE_TRANSACTIONS: str = "Transactions"

    # --- WhatsApp / Chatwoot (used by n8n, exposed here for manual trigger endpoints) ---
    CHATWOOT_BASE_URL: str = ""
    CHATWOOT_API_TOKEN: str = ""
    CHATWOOT_INBOX_ID: str = ""

    # --- Session cookie ---
    SESSION_COOKIE_NAME: str = "clearflow_session"
    SESSION_MAX_AGE_SECONDS: int = 60 * 60 * 24 * 7  # 7 days

    # --- CORS ---
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
