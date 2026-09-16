from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import courses, feedback, generation, notifications, progress

settings = get_settings()

app = FastAPI(title="Course Builder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(courses.router)
app.include_router(progress.router)
app.include_router(generation.router)
app.include_router(feedback.router)
app.include_router(notifications.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
