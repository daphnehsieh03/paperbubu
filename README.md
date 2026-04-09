# Papertrail — Research Paper Tracker

Monorepo: **FastAPI + SQLModel + PostgreSQL** (or SQLite for local quickstart) backend, **Next.js (App Router) + Tailwind + TanStack Query** frontend.

## Prerequisites

- Python 3.11+
- Node.js 18+ (tested with 22)
- Optional: Docker for PostgreSQL (`docker compose up -d`)

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Copy environment:

```bash
cp .env.example .env
```

- For **PostgreSQL** (recommended): set `DATABASE_URL=postgresql+psycopg://papertrail:papertrail@127.0.0.1:5432/papertrail` and start Postgres (`docker compose up -d` from repo root).
- For **SQLite** (no Docker): set `DATABASE_URL=sqlite:///./papertrail.db` in `.env`.

**Migrations:** Schema is managed with **Alembic** (`backend/alembic/`). On startup the API runs `alembic upgrade head`. You can also run manually from `backend/`:

```bash
alembic upgrade head
```

If you already have tables from an older `create_all` build and Alembic complains that tables exist, either use a fresh database file or align the schema and run `alembic stamp head` once (advanced).

After model changes, generate a new revision (with `DATABASE_URL` pointing at a reachable DB):

```bash
alembic revision --autogenerate -m "describe_change"
```

**Uploads:** PDFs are stored under `UPLOAD_DIR` (default `./uploads` relative to `backend/`). That directory is gitignored; do not commit PDFs.

Run API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- REST base: `http://localhost:8000/v1`
- Health: `http://localhost:8000/health`

Passwords are hashed with **passlib + bcrypt** (never `hashlib` for passwords).

## Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Run:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Register, then import PDFs or arXiv/DOI links, manage status (completions feed the heatmap via `DailyLog`), and browse the library with search.

## Docker Compose (PostgreSQL only)

```bash
docker compose up -d
```

Creates user/db `papertrail` / `papertrail` on port `5432`.

## API overview

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/auth/register`, `/v1/auth/login` | JWT bearer auth |
| GET | `/v1/papers` | List papers (`status`, `q`) |
| POST | `/v1/papers` | Create: JSON `{ "url" }` or multipart `file` (PDF) |
| GET | `/v1/papers/{id}` | Detail |
| PATCH | `/v1/papers/{id}` | Update; `status: completed` appends `DailyLog` once |
| DELETE | `/v1/papers/{id}` | Delete paper and stored file |
| POST | `/v1/papers/{id}/open` | Touch `last_opened_at` |
| GET | `/v1/me/heatmap` | Completion counts by day |
| GET | `/v1/me/stats` | Totals, keywords, recent lists |
