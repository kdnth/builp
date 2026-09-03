# builp

Learn by building. Write, generate, and work through courses consisting of written lessons, runnable code practice, and interactive activities.

Live at [builp.kdnth.co](https://builp.kdnth.co).

## Stack

- **Frontend**: React, TypeScript, Vite, Mantine
- **Backend**: FastAPI, SQLAlchemy, Alembic, Postgres
- **Auth**: Neon Auth
- **Course generation**: LangGraph, Claude (Anthropic)

## Project layout

```
frontend/   React app
backend/    FastAPI app, database, course generation
docs/       Design notes and plans
```

## Setup

You need:

- Node 20 or later
- Python 3.12 or later, and [uv](https://docs.astral.sh/uv/)
- A [Neon](https://neon.tech) project, with Neon Auth turned on
- An [Anthropic API key](https://console.anthropic.com), for course generation

### Backend

```bash
cd backend
cp .env.example .env
# fill in DATABASE_URL, NEON_AUTH_URL, ANTHROPIC_API_KEY
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Details on the API, tests, and migrations: [backend/README.md](backend/README.md).

### Frontend

```bash
cd frontend
cp .env.example .env.local
# fill in VITE_NEON_AUTH_URL
npm install
npm run dev
```

Open http://localhost:5173.

## Roadmap

- Code practice support for more languages, not just JavaScript
- Code practice IDE improvements: type hints, tab indenting, custom test cases
- More interactive activity types

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
