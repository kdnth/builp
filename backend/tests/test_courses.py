def test_list_courses_starts_empty(client):
    response = client.get("/api/courses")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_fetch_course(client, sample_course):
    created = client.post("/api/courses", json=sample_course)
    assert created.status_code == 201
    assert created.json()["id"] == "test-course"

    listed = client.get("/api/courses").json()
    assert listed == [
        {
            "id": "test-course",
            "title": "Test Course",
            "unit_count": 1,
            "lesson_count": 1,
        }
    ]

    fetched = client.get("/api/courses/test-course")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Test Course"


def test_create_course_rejects_missing_field(client, sample_course):
    del sample_course["units"][0]["lessons"][0]["writtenLesson"]
    response = client.post("/api/courses", json=sample_course)
    assert response.status_code == 422


def test_create_course_rejects_bad_discriminator(client, sample_course):
    sample_course["units"][0]["lessons"][0]["interactivePractices"][0]["activities"][0][
        "type"
    ] = "notAType"
    response = client.post("/api/courses", json=sample_course)
    assert response.status_code == 422


def test_create_course_rejects_duplicate_id(client, sample_course):
    first = client.post("/api/courses", json=sample_course)
    assert first.status_code == 201

    second = client.post("/api/courses", json=sample_course)
    assert second.status_code == 409


def test_get_missing_course_is_404(client):
    response = client.get("/api/courses/does-not-exist")
    assert response.status_code == 404


def test_create_course_without_auth_is_rejected(client, sample_course):
    from app.auth import get_current_user
    from app.config import Settings, get_settings
    from app.main import app

    # Force a deterministic "auth not configured" state for the real
    # dependency, rather than depending on whether this machine happens to
    # have a backend/.env with real Neon Auth values in it.
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides[get_settings] = lambda: Settings(
        neon_auth_url=None, neon_auth_jwks_url=None
    )
    try:
        response = client.post("/api/courses", json=sample_course)
    finally:
        from app.auth import AuthenticatedUser

        app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
            id="user-1"
        )
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 503
    assert client.get("/api/courses").json() == []
