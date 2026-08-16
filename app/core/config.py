"""Application configuration loaded from environment variables.

All settings are typed and validated by Pydantic Settings. Secrets must NEVER
be hardcoded — they are read exclusively from the environment / `.env` file.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "testing", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_env: Environment = "development"
    app_name: str = "Sevanna API"
    app_debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Database ---
    database_url: str = "postgresql+asyncpg://sevanna:sevanna@localhost:5432/sevanna"

    # --- JWT / Auth ---
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    password_reset_token_expire_minutes: int = 30
    email_verification_token_expire_hours: int = 48

    # --- CORS ---
    frontend_url: str = "http://localhost:5173"
    # NoDecode: don't JSON-decode this env value; the validator below splits a
    # comma-separated string (e.g. "http://a.com,http://b.com") into a list.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    # --- Docs ---
    enable_docs: bool = True

    # --- Payment provider ---
    payment_provider: Literal["wompi", "fake"] = "fake"
    payment_api_key: str = ""
    payment_public_key: str = ""
    payment_webhook_secret: str = ""  # Wompi "events" secret (webhook signature)
    payment_integrity_secret: str = ""  # Wompi "integrity" secret (checkout signature)
    payment_base_url: str = "https://sandbox.wompi.co/v1"
    payment_checkout_url: str = "https://checkout.wompi.co/p/"
    payment_currency: str = "COP"
    payment_redirect_url: str = "http://localhost:5173/checkout/result"

    # --- Email provider ---
    email_provider: Literal["smtp", "console"] = "console"
    email_from: str = "no-reply@sevanna.co"
    email_from_name: str = "Sevanna"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True

    # --- Storage provider ---
    storage_provider: Literal["local"] = "local"
    storage_local_dir: str = "./media"
    storage_public_base_url: str = "http://localhost:8000/media"

    # --- First admin bootstrap ---
    first_admin_email: str = "admin@sevanna.co"
    first_admin_password: str = "ChangeMe123!"
    first_admin_name: str = "Administrador Sevanna"

    # --- Rate limiting ---
    rate_limit_enabled: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Allow CORS_ORIGINS to be provided as a comma-separated string."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def docs_url(self) -> str | None:
        return "/docs" if self.enable_docs else None

    @property
    def redoc_url(self) -> str | None:
        return "/redoc" if self.enable_docs else None

    @property
    def openapi_url(self) -> str | None:
        return "/openapi.json" if self.enable_docs else None


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton (safe for import across the app)."""
    return Settings()


settings = get_settings()
