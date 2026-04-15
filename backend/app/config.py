from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Use docker-compose Postgres in production-like dev; sqlite works without Docker.
    database_url: str = "postgresql+psycopg://papertrail:papertrail@127.0.0.1:5432/papertrail"
    redis_url: str = "redis://127.0.0.1:6379/0"
    upload_dir: str = "./uploads"
    cors_origins: str = "http://localhost:3000"
    jwt_secret: str = "change-me-in-production-use-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 14
    refresh_cookie_name: str = "refresh_token"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"


settings = Settings()
