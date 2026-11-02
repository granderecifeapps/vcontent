from datetime import datetime, timezone

from pydantic_settings import BaseSettings, SettingsConfigDict


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Settings(BaseSettings):
    app_env: str = "development"
    app_version: str = "1.0.0"
    database_url: str = "postgresql+psycopg://vcontent:vcontent@localhost:5433/vcontent"
    secret_key: str = "troque-esta-chave"
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:3010"
    frontend_url: str = "http://localhost:3010"
    s3_endpoint: str = "http://localhost:9000"
    s3_public_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "vcontent"
    s3_region: str = "us-east-1"
    admin_email: str = "admin@vcontent.local"
    admin_password: str = "Admin!2026"
    admin_name: str = "Administradora"
    max_image_mb: int = 15
    max_video_mb: int = 200
    rate_limit_enabled: bool = True
    blob_read_write_token: str = ""
    public_api_url: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    drive_folder_id: str = ""
    drive_account_email: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def expose_dev_reset(self) -> bool:
        return self.app_env in {"development", "test"}


settings = Settings()
