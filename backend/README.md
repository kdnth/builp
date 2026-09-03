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
- `POST /api/generation-jobs` - start generating a course with AI. Requires auth. Returns immediately with a job id; runs as a background task. Supports two modes:
  - `generation_mode=free_credit` (default): server-managed provider key, one request per rolling 24-hour window per user.
  - `generation_mode=provider_api_key`: user supplies `provider` (`anthropic`, `openai`, `groq`, `xai`, `mistral`, `gemini`, `ollama`, or `deepseek`) and `provider_api_key`, and this bypasses the free-credit rate limit.
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

Provider support and key handling:

- Free-credit mode uses the server-managed Anthropic key (`ANTHROPIC_API_KEY`).
- Provider-key mode supports `anthropic`, `openai`, `groq`, `xai`, `mistral`, `gemini`, `ollama`, and `deepseek`.
- User-supplied keys are passed to the background generation task in memory
  only; they are never written to database rows or persisted in logs.
- Ollama usually runs unauthenticated; if your server has no auth, pass a
  non-empty placeholder value (for example `ollama`) as `provider_api_key`.

Without `ANTHROPIC_API_KEY`, free-credit jobs still get accepted, but those
jobs fail with a clear error instead of silently doing nothing.

### Default provider tier maps

These are the defaults used by `app/agent/llm.py` for stage tiering:

- `anthropic`: `fast=claude-haiku-4-5`, `standard=claude-sonnet-5`, `strong=claude-opus-5`
- `openai`: `fast=gpt-4o-mini`, `standard=gpt-4o`, `strong=gpt-4.1`
- `groq`: `fast=llama-3.1-8b-instant`, `standard=llama-3.3-70b-versatile`, `strong=deepseek-r1-distill-llama-70b`
- `xai`: `fast=grok-3-mini`, `standard=grok-3`, `strong=grok-4`
- `mistral`: `fast=ministral-8b-latest`, `standard=mistral-small-latest`, `strong=mistral-large-latest`
- `gemini`: `fast=gemini-2.5-flash-lite`, `standard=gemini-2.5-flash`, `strong=gemini-2.5-pro`
- `ollama`: `fast=llama3.1:8b`, `standard=llama3.1:70b`, `strong=deepseek-r1:32b`
- `deepseek`: `fast=deepseek-chat`, `standard=deepseek-chat`, `strong=deepseek-reasoner`

### Provider endpoint and model overrides

All non-Anthropic providers run through OpenAI-compatible chat transport.
Defaults can be overridden without code changes:

- Base URL override env vars: `OPENAI_BASE_URL`, `GROQ_BASE_URL`,
  `XAI_BASE_URL`, `MISTRAL_BASE_URL`, `GEMINI_BASE_URL`,
  `OLLAMA_BASE_URL`, `DEEPSEEK_BASE_URL`
- Model override pattern:
  `COURSE_GEN_MODEL_<PROVIDER>_<TIER>` (for example
  `COURSE_GEN_MODEL_OLLAMA_STANDARD=qwen2.5:32b`)

## Auth

Auth checks for Neon Auth (built on Better Auth, tokens signed with EdDSA /
Ed25519). See `app/auth.py`. Until `NEON_AUTH_URL` (or `NEON_AUTH_JWKS_URL`)
is set in `.env`, every auth-protected route returns `503 Auth is not set up
on the server yet.` instead of trying to verify a token.
