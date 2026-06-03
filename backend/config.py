"""Configuration management for Cipher Frame using environment variables."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Cipher Frame"
    environment: str = "development"
    debug: bool = False
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])
    database_path: str = "storage/cipher_frame.db"
    log_level: str = "INFO"
    secret_key: str
    access_token_expire_minutes: int = 60
    max_image_upload_bytes: int = 5_242_880
    allowed_image_types: list[str] = Field(default_factory=lambda: ["png", "jpeg", "gif", "webp", "bmp"])
    default_admin_username: str = "admin"
    default_admin_email: str = "admin@cipherframe.local"
    default_admin_password: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        """Allow origins to be configured as a comma-separated string."""

        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if value is None:
            return []
        return list(value)

    @field_validator("allowed_image_types", mode="before")
    @classmethod
    def parse_allowed_image_types(cls, value: object) -> list[str]:
        """Allow image types to be configured as a comma-separated string."""

        if isinstance(value, str):
            return [image_type.strip().lower() for image_type in value.split(",") if image_type.strip()]
        if value is None:
            return []
        return [str(image_type).lower() for image_type in value]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance for the application lifetime."""

    return Settings()
