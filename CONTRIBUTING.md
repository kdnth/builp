# Contributing

## Setup

See the [README](README.md) for local setup.

## Before you open a PR

Backend:

```bash
cd backend
uv run pytest
uv run ruff check .
uv run ruff format .
```

Frontend:

```bash
cd frontend
npx tsc -b --noEmit
npm run lint
```

Both must pass clean.

## Conventions

- Backend: Python 3.12+, type hints throughout, Pydantic for every request
  and response shape.
- Frontend: TypeScript strict mode, Mantine for UI, Zod for client-side
  validation of uploaded course files.
- Course JSON is validated independently on both ends:
  `frontend/src/schemas/course.ts` and `backend/app/schemas/course.py`.
  Keep them in sync if you change the course shape.
- Schema changes go through an Alembic migration
  (`uv run alembic revision --autogenerate -m "..."`). Read the generated
  migration before running it.
- New backend behavior needs a test. `backend/tests/` mirrors `backend/app/`.

## Commits and PRs

- Keep commits focused. Good rule of thumb: one logical change per commit.
- Explain why a change was made, not just what changed.
- Open a PR against `main`. Link an issue if one exists.

## Reporting bugs

Open an issue. Include steps to reproduce and what you expected instead.
