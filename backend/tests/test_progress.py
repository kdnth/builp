def test_progress_starts_empty(client, sample_course):
    course_id = client.post("/api/courses", json=sample_course).json()["id"]
    response = client.get(f"/api/courses/{course_id}/progress")
    assert response.status_code == 200
    assert response.json() == {
        "course_id": course_id,
        "completed_lesson_ids": [],
    }


def test_progress_for_missing_course_is_404(client):
    response = client.get("/api/courses/does-not-exist/progress")
    assert response.status_code == 404


def test_complete_lesson_is_idempotent(client, sample_course):
    course_id = client.post("/api/courses", json=sample_course).json()["id"]

    first = client.post(f"/api/courses/{course_id}/progress/lessons/l1/complete")
    assert first.status_code == 200
    first_completed_at = first.json()["completed_at"]

    second = client.post(f"/api/courses/{course_id}/progress/lessons/l1/complete")
    assert second.status_code == 200
    assert second.json()["completed_at"] == first_completed_at

    progress = client.get(f"/api/courses/{course_id}/progress").json()
    assert progress["completed_lesson_ids"] == ["l1"]


def test_progress_is_scoped_per_user(client, sample_course, current_user):
    from app.auth import AuthenticatedUser, get_current_user
    from app.main import app

    course_id = client.post("/api/courses", json=sample_course).json()["id"]
    client.post(f"/api/courses/{course_id}/progress/lessons/l1/complete")

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="user-2")
    try:
        other_users_progress = client.get(
            f"/api/courses/{course_id}/progress"
        ).json()
    finally:
        app.dependency_overrides[get_current_user] = lambda: current_user

    assert other_users_progress["completed_lesson_ids"] == []


def _create_course_as(client, sample_course, user_id):
    from app.auth import AuthenticatedUser, get_current_user, get_current_user_optional
    from app.main import app

    original = app.dependency_overrides[get_current_user]
    original_optional = app.dependency_overrides[get_current_user_optional]
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id=user_id)
    app.dependency_overrides[get_current_user_optional] = lambda: AuthenticatedUser(
        id=user_id
    )
    try:
        return client.post("/api/courses", json=sample_course).json()["id"]
    finally:
        app.dependency_overrides[get_current_user] = original
        app.dependency_overrides[get_current_user_optional] = original_optional


def test_complete_lesson_requires_saved_course(client, sample_course):
    course_id = _create_course_as(client, sample_course, "author")

    response = client.post(f"/api/courses/{course_id}/progress/lessons/l1/complete")
    assert response.status_code == 403
    assert client.get(f"/api/courses/{course_id}/progress").json()[
        "completed_lesson_ids"
    ] == []

    client.post(f"/api/courses/{course_id}/save")
    response = client.post(f"/api/courses/{course_id}/progress/lessons/l1/complete")
    assert response.status_code == 200


def test_course_detail_reports_saved_status(client, sample_course):
    owned_id = client.post("/api/courses", json=sample_course).json()["id"]
    assert client.get(f"/api/courses/{owned_id}").json()["saved"] is True

    others_id = _create_course_as(client, sample_course, "author")
    assert client.get(f"/api/courses/{others_id}").json()["saved"] is False

    client.post(f"/api/courses/{others_id}/save")
    assert client.get(f"/api/courses/{others_id}").json()["saved"] is True


def test_course_detail_is_unsaved_for_anonymous_viewer(client, sample_course):
    from app.auth import get_current_user_optional
    from app.main import app

    course_id = client.post("/api/courses", json=sample_course).json()["id"]
    app.dependency_overrides[get_current_user_optional] = lambda: None
    response = client.get(f"/api/courses/{course_id}")
    assert response.status_code == 200
    assert response.json()["saved"] is False


def test_unsave_deletes_progress(client, sample_course):
    course_id = _create_course_as(client, sample_course, "author")
    client.post(f"/api/courses/{course_id}/save")
    client.post(f"/api/courses/{course_id}/progress/lessons/l1/complete")

    assert client.delete(f"/api/courses/{course_id}/save").status_code == 204
    assert client.get(f"/api/courses/{course_id}/progress").json()[
        "completed_lesson_ids"
    ] == []
