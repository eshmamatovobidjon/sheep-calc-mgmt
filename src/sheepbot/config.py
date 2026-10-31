from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str
    admin_telegram_id: int
    database_url: str = "sqlite+aiosqlite:///./storage/app.db"
    storage_dir: Path = Path("./storage")
    timezone: str = "Asia/Tashkent"
    log_level: str = "INFO"
    company_name: str = ""
    max_upload_mb: int = 10

    @property
    def uploads_dir(self) -> Path:
        return self.storage_dir / "uploads"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
