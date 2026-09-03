def test_progress_starts_empty(client, sample_course):
    client.post("/api/courses", json=sample_course)
    response = client.get("/api/courses/test-course/progress")
    assert response.status_code == 200
    assert response.json() == {
        "course_id": "test-course",
        "completed_lesson_ids": [],
    }


def test_progress_for_missing_course_is_404(client):
    response = client.get("/api/courses/does-not-exist/progress")
    assert response.status_code == 404


def test_complete_lesson_is_idempotent(client, sample_course):
    client.post("/api/courses", json=sample_course)

    first = client.post("/api/courses/test-course/progress/lessons/l1/complete")
    assert first.status_code == 200
    first_completed_at = first.json()["completed_at"]

    second = client.post("/api/courses/test-course/progress/lessons/l1/complete")
    assert second.status_code == 200
    assert second.json()["completed_at"] == first_completed_at

    progress = client.get("/api/courses/test-course/progress").json()
    assert progress["completed_lesson_ids"] == ["l1"]


def test_progress_is_scoped_per_user(client, sample_course, current_user):
    from app.auth import AuthenticatedUser, get_current_user
    from app.main import app

    client.post("/api/courses", json=sample_course)
    client.post("/api/courses/test-course/progress/lessons/l1/complete")

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="user-2")
    try:
        other_users_progress = client.get("/api/courses/test-course/progress").json()
    finally:
        app.dependency_overrides[get_current_user] = lambda: current_user

    assert other_users_progress["completed_lesson_ids"] == []
