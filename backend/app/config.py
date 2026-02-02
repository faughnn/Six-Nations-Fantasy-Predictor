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
    model_path: str = "models/fantasy_predictor_v1.pkl"

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
