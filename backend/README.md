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

The last retry attempt of a stage normally escalates to `strong` as a
quality backstop, but not when every attempt so far failed the cheap
deterministic check (wrong unit/lesson count, wrong shape) with `generate`
producing valid output each time - a stronger model has no particular
edge at counting correctly, so that specific pattern stays on the
default tier instead (`app/agent/stage.py`).

### Model overrides

Defaults can be overridden without code changes via
`COURSE_GEN_MODEL_<PROVIDER>_<TIER>` (for example
`COURSE_GEN_MODEL_ANTHROPIC_STANDARD=claude-sonnet-5`).

### Token budget (cost safety net)

Every job gets a hard token ceiling, sized from what it actually asked for
(`app/agent/budget.py`). If a job's total tokens cross the ceiling - most
often because the model kept returning more units or lessons than
requested, and the deterministic checks never converged - the job stops and
is marked `failed` with a clear "over the token budget" message, instead of
continuing to spend indefinitely.

The ceiling is `screening + per_unit * num_units + per_lesson * num_units *
lessons_per_unit`. Override the per-piece allowances without code changes:

- `COURSE_GEN_TOKEN_BUDGET_SCREENING` (default 5,000)
- `COURSE_GEN_TOKEN_BUDGET_PER_UNIT` (default 40,000)
- `COURSE_GEN_TOKEN_BUDGET_PER_LESSON` (default 90,000)

This bounds a job to roughly what it requested, not to whatever the model
decides to generate - a job that balloons past its own request hits the
ceiling on the stage it's currently in, before that stage's output can fan
out into the next (and far more expensive) one. It is not a mid-call
kill switch: calls already in flight when the ceiling is crossed still
finish and report their usage, so a bad run can overshoot by roughly one
stage's worth of parallel work before stopping - it does not run
unbounded.

### Narrow retry for activity-only lesson failures

A lesson retry normally rewrites the whole lesson (write, solve, judge)
even when only one activity was the problem. `generate_lesson_content`
(`app/agent/nodes.py`) takes a smaller "activities only" retry path
instead, but only when a retry is proven to be activity-scoped:

- `check_lesson_content_split` (`app/agent/checks.py`) separates
  deterministic problems into structural (code practice) and activity
  buckets, so a check failure with no structural problems is activity-only.
- The solver (`app/agent/solver.py`) only ever inspects activities, so an
  objection from it is also activity-only.

On that narrow path only, the retry asks the model for new activities for
the existing written sections (`lesson_activities_fix_prompt` in
`app/agent/prompts.py`), and merges the result back onto the last draft
instead of generating the lesson again from scratch. Any structural
failure, any judge-quality failure, or the first attempt still takes the
full-lesson path, so the common case costs the same as generating the
whole lesson in one call. This was chosen over always splitting lesson
generation into two calls (write, then activities) because most lessons
pass without a retry at all, and paying the split's extra call on every
lesson would cost more than only paying it on the retries that need it.

The model does not reliably return exactly one activities list per
section despite being asked to - a 2026-09-22 golden-set analysis found
this failing on close to half of these narrow-fix calls. `_merge_activity_fix`
degrades instead of raising when the count is off, matching each fix
entry to a section by the `section_index` the model reports rather than
by list position: a section the fix didn't cover keeps its own original
activities unchanged. A section that still has a real problem gets caught
again by the next `check()` and costs a normal retry, instead of the call
being wasted and silently forcing the next attempt to a stronger,
costlier tier for something the model was never actually wrong about (see
`app/agent/stage.py`'s `only_structural_failures_so_far`, which escalates
unconditionally on any `generate()` exception). Matching by position
alone (an earlier version of this fix) could silently apply one section's
fix to a different section whenever the fix response didn't cover every
section in order; matching by `section_index` removes that ambiguity
regardless of order or count.

### The overview judge no longer fights the requested unit count

`overview_evaluate_prompt` (`app/agent/prompts.py`) now tells the judge
how many units were required. Before this, the judge was never told a
count was fixed by the caller, so it graded every course overview against
an implicit assumption that a real course needs several units - and
failed a compliant, correctly-sized overview every time the caller asked
for few units, while the deterministic unit-count check simultaneously
rejected any attempt to fix that by adding more. A 2026-09-22 golden-set
analysis found this made the overview stage's pass rate 0% in every run,
burning a guaranteed `strong`-tier call on every course for a fight the
model could never win. The rubric (`OVERVIEW_EVAL_SYSTEM`) now judges
scope and progression within the fixed count instead of penalizing the
count itself.

### `generate()` exceptions are now visible in metrics

A model call inside a stage's `generate()` step can raise (invalid JSON,
a schema-validation failure, or an application-level check like the merge
above). Before this, `run_stage_with_retries` (`app/agent/stage.py`)
treated that the same as a failed check - useful for the retry itself -
but never recorded that it happened anywhere, so it was invisible to
metrics and the golden-set report. `StageOutcome.generate_errors` now
captures each one (with the attempt number, tier, and exception text),
threaded through `StageMetrics`, `summarize_job_metrics`, and the
golden-set report's new "generate() exceptions" section and
`generate_exceptions_by_stage` totals line.

### Golden set

The golden set generates 8 fixed topics (one or more for each lesson profile)
and checks 6 screening cases. Run it after a prompt or pipeline change. It
calls the real model with `ANTHROPIC_API_KEY`, so it costs money, and it is
not part of the test suite.

```bash
uv run python scripts/eval_generation.py --dry-run
uv run python scripts/eval_generation.py --yes
uv run python scripts/eval_generation.py --yes --only ww1-causes,bike-tire
```

Each run writes `eval-runs/<timestamp>/` (not tracked by git) with
`report.md`, `results.json`, and the generated courses. The report's
decision hints come from `app/agent/evaluation.py`. Per-topic spend is
capped by the same token budget a real job gets (see "Token budget" above),
so a bad run stops early instead of repeating the 2026-09-17 cost incident.

The report tracks lesson retry causes, judge scores by profile, and token
and call counts - watch these across runs to catch a prompt or pipeline
change that quietly makes generation slower, costlier, or worse. One hint
is specific to the narrow retry (see "Narrow retry for activity-only
lesson failures" above): it reports how many failed lesson attempts were
activity-shaped against how many activities-only fix calls actually ran.
Those two numbers track together in the common case; a growing gap is
worth a look at the attempts in `results.json`, since it means fewer
activity-shaped failures are getting the cheaper fix than expected.

## Auth

Auth checks for Neon Auth (built on Better Auth, tokens signed with EdDSA /
Ed25519). See `app/auth.py`. Until `NEON_AUTH_URL` (or `NEON_AUTH_JWKS_URL`)
is set in `.env`, every auth-protected route returns `503 Auth is not set up
on the server yet.` instead of trying to verify a token.
