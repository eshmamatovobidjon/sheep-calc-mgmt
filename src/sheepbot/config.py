from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str
    admin_telegram_id: int
    database_url: str = "postgresql+asyncpg://sheepbot:sheepbot@localhost:5432/sheepbot"
    storage_dir: Path = Path("./storage")
    timezone: str = "Asia/Tashkent"
    log_level: str = "INFO"
    company_name: str = ""
    max_upload_mb: int = 10
    app_env: str = "prod"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    webapp_auth_max_age_hours: int = 24
    dev_auth_telegram_id: int | None = None
    web_dist_dir: Path = Path("web/dist")
    mini_app_url: str = ""

    @property
    def uploads_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def dev_auth_enabled(self) -> bool:
        """Requests without initData act as DEV_AUTH_TELEGRAM_ID. Only with APP_ENV=dev."""
        return self.app_env == "dev" and self.dev_auth_telegram_id is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
