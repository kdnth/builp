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

- `GET /api/courses?q=&tag=` - list courses (id, title, unit/lesson count, tags, owner). No auth. `q` matches the title, `tag` filters to an exact tag.
- `GET /api/courses/{course_id}` - full course document plus tags and owner. No auth.
- `POST /api/courses` - create a course from a full course JSON document. Requires auth. Rejects a course whose `id` already exists.
- `PATCH /api/courses/{course_id}/tags` - replace a course's tags. Requires auth. Only the course's author can call this.
- `GET /api/courses/{course_id}/progress` - the signed-in user's completed lesson ids for a course. Requires auth.
- `POST /api/courses/{course_id}/progress/lessons/{lesson_id}/complete` - mark a lesson complete for the signed-in user. Requires auth. Safe to call more than once.
- `POST /api/generation-jobs` - start generating a course with AI. Requires auth. Returns immediately with a job id; runs as a background task.
- `GET /api/generation-jobs/{job_id}` - poll a generation job's status. Requires auth. Returns the new course's id once it succeeds.

Course documents are validated against `app/schemas/course.py`, which
mirrors `frontend/src/schemas/course.ts` field for field. The backend never
trusts frontend validation. It checks again on every upload. Tags and
authorship are stored separately from the course document itself, so they
never need a schema migration on the frontend side.

## AI course generation

`app/agent/` holds the course-writing pipeline: overview, then units, then
lessons, each generated and checked before moving on. See
`docs/plans/course-generation-agent.md` at the repo root for the design.
Needs `ANTHROPIC_API_KEY` set. Without it, `POST /api/generation-jobs`
still accepts the request, but the job fails with a clear error instead of
silently doing nothing.

## Auth

Auth checks for Neon Auth (built on Better Auth, tokens signed with EdDSA /
Ed25519). See `app/auth.py`. Until `NEON_AUTH_URL` (or `NEON_AUTH_JWKS_URL`)
is set in `.env`, every auth-protected route returns `503 Auth is not set up
on the server yet.` instead of trying to verify a token.
