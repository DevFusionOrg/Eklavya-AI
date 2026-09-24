from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Eklavya.AI API"
    app_version: str = "0.1.0"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://eklavya:change-me@postgres:5432/eklavya"
    redis_url: str = "redis://redis:6379/0"
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    log_level: str = "INFO"
    jwt_secret: str = "replace-with-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    auth_rate_limit: int = 10
    auth_rate_window_seconds: int = 60
    max_login_failures: int = 5
    lockout_minutes: int = 15
    minio_bucket: str = "eklavya-documents"
    document_max_size_bytes: int = 10 * 1024 * 1024
    document_max_sizes: dict[str, int] = Field(default_factory=dict)
    document_url_expiry_seconds: int = 300
    ocr_engine: str = "mock"
    ocr_languages: list[str] = Field(default_factory=lambda: ["en", "hi"])
    ocr_task_max_retries: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def minio_url(self) -> str:
        scheme = "https" if self.minio_secure else "http"
        return f"{scheme}://{self.minio_endpoint}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
