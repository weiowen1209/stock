from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "Humanoid Robot Stock Dashboard"
    environment: str = Field(default="development", validation_alias="APP_ENV")
    database_url: str = Field(
        default=f"sqlite+aiosqlite:///{(BASE_DIR / 'data' / 'dashboard.db').as_posix()}",
        validation_alias="DATABASE_URL",
    )
    upload_dir: Path = Field(default=BASE_DIR / "data" / "uploads", validation_alias="UPLOAD_DIR")
    enable_mock_data: bool = False
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        validation_alias="CORS_ORIGINS",
    )
    provider_timeout_seconds: int = Field(default=10, validation_alias="PROVIDER_TIMEOUT_SECONDS")
    provider_failure_threshold: int = Field(default=3, validation_alias="PROVIDER_FAILURE_THRESHOLD")
    provider_probe_interval_minutes: int = Field(
        default=30, validation_alias="PROVIDER_PROBE_INTERVAL_MINUTES"
    )
    sync_concurrency: int = Field(default=6, validation_alias="SYNC_CONCURRENCY")
    sync_batch_size: int = Field(default=500, validation_alias="SYNC_BATCH_SIZE")

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        enable_decoding=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def sqlite_path(self) -> Path:
        if not self.database_url.startswith("sqlite+aiosqlite:///"):
            raise ValueError("Only sqlite+aiosqlite database URLs are supported in stage 1")
        return Path(self.database_url.replace("sqlite+aiosqlite:///", ""))


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings
