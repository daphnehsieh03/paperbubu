from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.db import engine, run_migrations
from app.routers import analytics, auth, papers
from app.token_store import get_redis


def _is_postgres() -> bool:
    return "postgresql" in settings.database_url


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_redis().ping()
    run_migrations()
    if _is_postgres():
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        with engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_paper_search_trgm ON paper USING gin (search_document gin_trgm_ops)"
                )
            )
    yield


app = FastAPI(title="Papertrail API", lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/v1")
app.include_router(papers.router, prefix="/v1")
app.include_router(analytics.router, prefix="/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
