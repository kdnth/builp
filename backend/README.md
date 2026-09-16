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
- `DELETE /api/courses/{course_id}` - delete a course. Requires auth. Only the course's author can call this. Returns `204 No Content`.
- `GET /api/courses/{course_id}/progress` - the signed-in user's completed lesson ids for a course. Requires auth.
- `POST /api/courses/{course_id}/progress/lessons/{lesson_id}/complete` - mark a lesson complete for the signed-in user. Requires auth. Safe to call more than once.
- `POST /api/generation-jobs` - start generating a course with AI. Requires auth. Returns immediately with a job id; runs as a background task. Supports two modes:
  - `generation_mode=free_credit` (default): server-managed provider key, one request per rolling 24-hour window per user.
  - `generation_mode=provider_api_key`: user supplies `provider` (`anthropic`) and `provider_api_key`, and this bypasses the free-credit rate limit.
- `GET /api/generation-jobs/{job_id}` - poll a generation job's status. Requires auth. Returns the new course's id once it succeeds.
- `POST /api/feedback/contact` - general contact message. No auth, so signed-out visitors can reach support. Emails `CONTACT_EMAIL`. Capped at 5 submissions per IP per hour.
- `POST /api/feedback/courses/{course_id}/reports` - report a problem in one course. Requires auth. Emails `SUPPORT_EMAIL`, and writes the course author an in-app notification when that author is someone other than the reporter.
- `GET /api/notifications` - the signed-in user's newest notifications plus an unread count. Requires auth.
- `POST /api/notifications/{notification_id}/read` - mark one notification read. Requires auth. Another user's notification returns 404.
- `POST /api/notifications/read-all` - mark every unread notification read. Requires auth. Returns `204 No Content`.

Course documents are validated against `app/schemas/course.py`, which
mirrors `frontend/src/schemas/course.ts` field for field. The backend never
trusts frontend validation. It checks again on every upload. Tags and
authorship are stored separately from the course document itself, so they
never need a schema migration on the frontend side.

## AI course generation

`app/agent/` holds the course-writing pipeline: overview, then units, then
lessons, each generated and checked before moving on. See
`docs/plans/course-generation-agent.md` at the repo root for the design.

Provider support and key handling:

- Free-credit mode uses the server-managed Anthropic key (`ANTHROPIC_API_KEY`).
- Provider-key mode currently supports `anthropic` only.
- User-supplied keys are passed to the background generation task in memory
  only; they are never written to database rows or persisted in logs.

Without `ANTHROPIC_API_KEY`, free-credit jobs still get accepted, but those
jobs fail with a clear error instead of silently doing nothing.

### Default model tier map

These are the defaults used by `app/agent/llm.py` for stage tiering:

- `anthropic`: `fast=claude-haiku-4-5`, `standard=claude-sonnet-5`, `strong=claude-opus-5`

### Model overrides

Defaults can be overridden without code changes via
`COURSE_GEN_MODEL_<PROVIDER>_<TIER>` (for example
`COURSE_GEN_MODEL_ANTHROPIC_STANDARD=claude-sonnet-5`).

## Auth

Auth checks for Neon Auth (built on Better Auth, tokens signed with EdDSA /
Ed25519). See `app/auth.py`. Until `NEON_AUTH_URL` (or `NEON_AUTH_JWKS_URL`)
is set in `.env`, every auth-protected route returns `503 Auth is not set up
on the server yet.` instead of trying to verify a token.

## Feedback and notifications

Two channels feed the same `feedback_submissions` table:

- The contact form, which emails `CONTACT_EMAIL` (hello@).
- Course problem reports, which email `SUPPORT_EMAIL` (support@) and notify
  the course author in the app.

Every submission is written to the database before any send is attempted, so
a bounced or unconfigured send loses the email, never the report. Delivery
runs in a `BackgroundTask` after the response, and flips
`feedback_submissions.email_delivered` on success. With `RESEND_API_KEY`
unset, `app/email.py` logs and returns without calling out, which is the
intended development behavior.

The contact endpoint is the one route here open to signed-out visitors, so it
caps submissions per client IP (see `_RATE_LIMIT_MAX_SUBMISSIONS` in
`app/routers/feedback.py`). The IP comes from the first `X-Forwarded-For`
hop, since the app sits behind a proxy in production.

Notifications are generic rows keyed by `user_id` and `kind`, not specific to
reports. The header bell polls `GET /api/notifications`.
