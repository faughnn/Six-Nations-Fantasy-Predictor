import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = os.environ.get(
        "DATABASE_URL",
        ""
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL environment variable is required. "
                "Run via docker-compose to set it automatically."
            )
        # Railway provides postgresql:// but asyncpg needs postgresql+asyncpg://
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        if not self.jwt_secret or self.jwt_secret == "change-me-in-production":
            raise ValueError(
                "JWT_SECRET environment variable must be set to a strong, unique value. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
    model_path: str = "models/fantasy_predictor_v1.pkl"

    # Auth settings
    jwt_secret: str = os.environ.get("JWT_SECRET", "")
    google_client_id: str = os.environ.get("GOOGLE_CLIENT_ID", "")

    # GitHub Issues
    github_token: str = os.environ.get("GITHUB_TOKEN", "")
    github_repo: str = os.environ.get("GITHUB_REPO", "")

    # CORS
    cors_origins: str = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
