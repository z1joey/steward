from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="STEWARDS_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost/steward"
    jwt_secret: str = "dev-only-change-me-0123456789abcdef"  # ≥32B；生产经 STEWARDS_JWT_SECRET 覆盖
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12


@lru_cache
def get_settings() -> Settings:
    return Settings()
