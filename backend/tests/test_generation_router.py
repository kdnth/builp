from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from app.models import GenerationJob


def _base_generation_payload(**overrides) -> dict[str, object]:
    payload: dict[str, object] = {
        "topic": "Python basics",
        "audience": "beginners",
        "num_units": 2,
        "lessons_per_unit": 2,
    }
    payload.update(overrides)
    return payload


def test_create_and_poll_generation_job(client):
    with patch("app.routers.generation.run_generation_job"):
        response = client.post(
            "/api/generation-jobs",
            json=_base_generation_payload(),
        )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["topic"] == "Python basics"
    assert body["course_id"] is None

    fetched = client.get(f"/api/generation-jobs/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


def test_create_generation_job_defaults(client):
    with patch("app.routers.generation.run_generation_job"):
        response = client.post(
            "/api/generation-jobs", json={"topic": "x", "audience": "y"}
        )
    body = response.json()
    assert body["num_units"] == 3
    assert body["lessons_per_unit"] == 3


def test_get_generation_job_not_found(client):
    response = client.get("/api/generation-jobs/does-not-exist")
    assert response.status_code == 404


def test_generation_job_is_scoped_per_user(client, current_user):
    from app.auth import AuthenticatedUser, get_current_user
    from app.main import app

    with patch("app.routers.generation.run_generation_job"):
        created = client.post(
            "/api/generation-jobs",
            json={"topic": "x", "audience": "y", "num_units": 1, "lessons_per_unit": 1},
        )
    job_id = created.json()["id"]

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="user-2")
    try:
        response = client.get(f"/api/generation-jobs/{job_id}")
    finally:
        app.dependency_overrides[get_current_user] = lambda: current_user

    assert response.status_code == 404


def test_create_generation_job_rate_limited(client):
    with patch("app.routers.generation.run_generation_job"):
        first = client.post(
            "/api/generation-jobs", json={"topic": "x", "audience": "y"}
        )
        assert first.status_code == 201

        second = client.post(
            "/api/generation-jobs", json={"topic": "x2", "audience": "y2"}
        )

    assert second.status_code == 429
    assert "24 hours" in second.json()["detail"]


def test_provider_api_key_mode_bypasses_rate_limit(client):
    with patch("app.routers.generation.run_generation_job"):
        first = client.post(
            "/api/generation-jobs", json={"topic": "x", "audience": "y"}
        )
        assert first.status_code == 201

        second = client.post(
            "/api/generation-jobs",
            json={
                "topic": "x2",
                "audience": "y2",
                "generation_mode": "provider_api_key",
                "provider": "openai",
                "provider_api_key": "sk-test",
            },
        )

    assert second.status_code == 201


@pytest.mark.parametrize(
    "provider", ["groq", "xai", "mistral", "gemini", "ollama", "deepseek"]
)
def test_provider_api_key_mode_accepts_new_supported_providers(client, provider):
    with patch("app.routers.generation.run_generation_job"):
        response = client.post(
            "/api/generation-jobs",
            json={
                "topic": "x",
                "audience": "y",
                "generation_mode": "provider_api_key",
                "provider": provider,
                "provider_api_key": "provider-key",
            },
        )

    assert response.status_code == 201


def test_provider_api_key_mode_passes_config_to_background_task(client):
    with patch("app.routers.generation.run_generation_job") as run_job:
        response = client.post(
            "/api/generation-jobs",
            json={
                "topic": "x",
                "audience": "y",
                "generation_mode": "provider_api_key",
                "provider": "openai",
                "provider_api_key": "sk-test",
            },
        )

    assert response.status_code == 201
    assert run_job.call_count == 1
    _, model_config = run_job.call_args.args
    assert model_config.provider == "openai"
    assert model_config.api_key == "sk-test"


def test_free_credit_mode_passes_server_managed_config(client):
    with patch("app.routers.generation.run_generation_job") as run_job:
        response = client.post(
            "/api/generation-jobs", json={"topic": "x", "audience": "y"}
        )

    assert response.status_code == 201
    assert run_job.call_count == 1
    _, model_config = run_job.call_args.args
    assert model_config.provider == "anthropic"
    assert model_config.api_key is None


def test_provider_api_key_mode_requires_provider(client):
    with patch("app.routers.generation.run_generation_job"):
        response = client.post(
            "/api/generation-jobs",
            json={
                "topic": "x",
                "audience": "y",
                "generation_mode": "provider_api_key",
                "provider_api_key": "sk-test",
            },
        )

    assert response.status_code == 400
    assert "provider is required" in response.json()["detail"]


def test_provider_api_key_mode_requires_key(client):
    with patch("app.routers.generation.run_generation_job"):
        response = client.post(
            "/api/generation-jobs",
            json={
                "topic": "x",
                "audience": "y",
                "generation_mode": "provider_api_key",
                "provider": "openai",
            },
        )

    assert response.status_code == 400
    assert "provider_api_key is required" in response.json()["detail"]


def test_provider_api_key_mode_rejects_blank_key(client):
    with patch("app.routers.generation.run_generation_job"):
        response = client.post(
            "/api/generation-jobs",
            json={
                "topic": "x",
                "audience": "y",
                "generation_mode": "provider_api_key",
                "provider": "openai",
                "provider_api_key": "   ",
            },
        )

    assert response.status_code == 400
    assert "provider_api_key is required" in response.json()["detail"]


def test_free_credit_mode_rejects_provider_credentials(client):
    with patch("app.routers.generation.run_generation_job"):
        response = client.post(
            "/api/generation-jobs",
            json={
                "topic": "x",
                "audience": "y",
                "generation_mode": "free_credit",
                "provider": "openai",
                "provider_api_key": "sk-test",
            },
        )

    assert response.status_code == 400
    assert "free_credit mode" in response.json()["detail"]


def test_create_generation_job_allowed_after_rate_limit_window(client, db_session):
    with patch("app.routers.generation.run_generation_job"):
        first = client.post(
            "/api/generation-jobs", json={"topic": "x", "audience": "y"}
        )
    assert first.status_code == 201

    job = db_session.get(GenerationJob, first.json()["id"])
    job.created_at = datetime.now(UTC) - timedelta(hours=25)
    db_session.commit()

    with patch("app.routers.generation.run_generation_job"):
        second = client.post(
            "/api/generation-jobs", json={"topic": "x2", "audience": "y2"}
        )

    assert second.status_code == 201


def test_generation_rate_limit_is_scoped_per_user(client, current_user):
    from app.auth import AuthenticatedUser, get_current_user
    from app.main import app

    with patch("app.routers.generation.run_generation_job"):
        first = client.post(
            "/api/generation-jobs", json={"topic": "x", "audience": "y"}
        )
    assert first.status_code == 201

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="user-2")
    try:
        with patch("app.routers.generation.run_generation_job"):
            other_user_response = client.post(
                "/api/generation-jobs", json={"topic": "x", "audience": "y"}
            )
    finally:
        app.dependency_overrides[get_current_user] = lambda: current_user

    assert other_user_response.status_code == 201


def test_create_generation_job_without_auth_is_rejected(client):
    from app.auth import get_current_user
    from app.config import Settings, get_settings
    from app.main import app

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides[get_settings] = lambda: Settings(
        neon_auth_url=None, neon_auth_jwks_url=None
    )
    try:
        response = client.post(
            "/api/generation-jobs", json={"topic": "x", "audience": "y"}
        )
    finally:
        from app.auth import AuthenticatedUser

        app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
            id="user-1"
        )
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 503
