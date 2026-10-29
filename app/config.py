from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    session_secret_key: str
    https_only: bool = False  # True in production (HTTPS)
    mongodb_uri: str | None = None
    mongodb_db: str = "oauth_app"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()