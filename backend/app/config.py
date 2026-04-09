from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Use docker-compose Postgres in production-like dev; sqlite works without Docker.
    database_url: str = "postgresql+psycopg://papertrail:papertrail@127.0.0.1:5432/papertrail"
    upload_dir: str = "./uploads"
    cors_origins: str = "http://localhost:3000"
    jwt_secret: str = "change-me-in-production-use-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7


settings = Settings()
