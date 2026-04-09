from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import Session, create_engine

from app.config import settings

_connect_args: dict = {}
if settings.database_url.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args=_connect_args or {},
)


def _alembic_config() -> Config:
    backend_root = Path(__file__).resolve().parent.parent
    ini_path = backend_root / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def run_migrations() -> None:
    """Apply Alembic migrations to head (replaces ad-hoc create_all)."""
    command.upgrade(_alembic_config(), "head")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
