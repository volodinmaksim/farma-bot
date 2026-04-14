from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    DB_URL: str
    BOT_TOKEN: SecretStr
    REDIS_URL: str | None = None
    RABBITMQ_URL: str | None = None
    BASE_URL: str
    WEBHOOK_IP_ADDRESS: str | None = None

    CHAT_ID_TO_CHECK: int
    CHAT_URL: str
    SECRET_TG_KEY: str
    YDISK_LINK: str

    HOST: str
    PORT: int
    RABBITMQ_PREFETCH: int = 1
    RABBITMQ_MAX_RETRIES: int = 5
    RABBITMQ_RETRY_DELAY_MS: int = 30000

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / "farma.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("WEBHOOK_IP_ADDRESS", mode="before")
    @classmethod
    def empty_strings_to_none(cls, value):
        if value == "":
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
