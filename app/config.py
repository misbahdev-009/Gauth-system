from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback"
    session_secret_key: str = "supersecret-session-key-change-in-production"
    https_only: bool = False  # Set to True in production with HTTPS
    mongodb_uri: str | None = None
    mongodb_db: str = "oauth_app"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def effective_https_only(self) -> bool:
        """Prevent Secure cookies on unencrypted localhost which breaks OAuth."""
        if self.google_redirect_uri.startswith("http://localhost") or self.google_redirect_uri.startswith("http://127.0.0.1"):
            return False
        return self.https_only


@lru_cache
def get_settings() -> Settings:
    return Settings()
