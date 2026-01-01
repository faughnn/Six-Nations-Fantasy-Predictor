import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = os.environ.get(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./fantasy_rugby.db"  # Default to SQLite for local dev
    )
    model_path: str = "models/fantasy_predictor_v1.pkl"

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
