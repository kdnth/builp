# Course Builder API

FastAPI backend for the course builder app. Stores courses and per-user
lesson progress in Postgres (Neon in production, SQLite for local dev if
you don't set `DATABASE_URL`).

## Setup

```bash
cd backend
cp .env.example .env   # fill in DATABASE_URL once you have a Neon project
uv sync
uv run alembic upgrade head
```

## Run the server

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Docs at http://localhost:8000/docs.

## Load the sample course

The frontend ships a sample course at
`frontend/src/data/courses/course-01.json`. Load it into the database with:

```bash
uv run python scripts/seed_courses.py
```

## Tests

```bash
uv run pytest
```

Tests run against an in-memory SQLite database and a fake authenticated
user, so they don't need `DATABASE_URL` or real Neon Auth credentials set.

## Lint and format

```bash
uv run ruff check .
uv run ruff format .
```

## Migrations

Schema changes go through Alembic. After changing a model in `app/models.py`:

```bash
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
```

Always read the generated migration before running it. Autogenerate is a
starting point, not a guarantee.

## API shape

- `GET /api/courses` - list courses (id, title, unit count, lesson count). No auth.
- `GET /api/courses/{course_id}` - full course document. No auth.
- `POST /api/courses` - create a course from a full course JSON document. Requires auth. Rejects a course whose `id` already exists.
- `GET /api/courses/{course_id}/progress` - the signed-in user's completed lesson ids for a course. Requires auth.
- `POST /api/courses/{course_id}/progress/lessons/{lesson_id}/complete` - mark a lesson complete for the signed-in user. Requires auth. Safe to call more than once.

Course documents are validated against `app/schemas/course.py`, which
mirrors `frontend/src/schemas/course.ts` field for field. The backend never
trusts frontend validation. It checks again on every upload.

## Auth

Auth checks for Neon Auth (built on Better Auth, tokens signed with EdDSA /
Ed25519). See `app/auth.py`. Until `NEON_AUTH_URL` (or `NEON_AUTH_JWKS_URL`)
is set in `.env`, every auth-protected route returns `503 Auth is not set up
on the server yet.` instead of trying to verify a token.
