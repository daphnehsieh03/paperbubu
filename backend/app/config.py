"""Application settings loaded from environment variables and an optional .env file.

No pydantic-settings — values are read with os.getenv and a minimal .env parser.
"""

import os
from pathlib import Path
from typing import Literal


def _load_dotenv(path: str = ".env") -> None:
    """Load key=value lines from *path* into os.environ (existing vars are never overwritten)."""
    env_file = Path(path)
    if not env_file.is_file():
        return
    for raw_line in env_file.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        # Strip optional surrounding quotes from the value
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://papertrail:papertrail@127.0.0.1:5432/papertrail",
        )
        self.redis_url: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
        self.upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")
        self.cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")

        # JWT
        self.jwt_secret: str = os.getenv(
            "JWT_SECRET", "change-me-in-production-use-long-random-string"
        )
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_access_expire_minutes: int = int(
            os.getenv("JWT_ACCESS_EXPIRE_MINUTES", "30")
        )
        self.jwt_refresh_expire_days: int = int(
            os.getenv("JWT_REFRESH_EXPIRE_DAYS", "14")
        )

        # Cookie
        self.refresh_cookie_name: str = os.getenv("REFRESH_COOKIE_NAME", "refresh_token")
        self.cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
        _samesite = os.getenv("COOKIE_SAMESITE", "lax").lower()
        if _samesite not in ("lax", "strict", "none"):
            _samesite = "lax"
        self.cookie_samesite: Literal["lax", "strict", "none"] = _samesite  # type: ignore[assignment]

        # PubMed
        self.pubmed_api_key: str = os.getenv("PUBMED_API_KEY", "")


settings = Settings()
