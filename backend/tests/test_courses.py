from app.models import Course as CourseModel


def test_list_courses_starts_empty(client):
    response = client.get("/api/courses")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_create_and_fetch_course(client, sample_course):
    created = client.post("/api/courses", json=sample_course)
    assert created.status_code == 201
    course_id = created.json()["id"]
    assert course_id != sample_course["id"]

    listed = client.get("/api/courses").json()
    assert listed == {
        "items": [
            {
                "id": course_id,
                "title": "Test Course",
                "unit_count": 1,
                "lesson_count": 1,
                "tags": [],
                "owner_user_id": "user-1",
                "saved": True,
            }
        ],
        "total": 1,
    }

    fetched = client.get(f"/api/courses/{course_id}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Test Course"
    assert fetched.json()["tags"] == []
    assert fetched.json()["owner_user_id"] == "user-1"
    assert fetched.json()["forkedFromId"] is None


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


def _first_code_practice(course: dict) -> dict:
    return course["units"][0]["lessons"][0]["codePractices"][0]


def test_function_practice_language_defaults_to_javascript(client, sample_course):
    course_id = client.post("/api/courses", json=sample_course).json()["id"]
    fetched = client.get(f"/api/courses/{course_id}").json()
    assert _first_code_practice(fetched)["language"] == "javascript"


def test_function_practice_keeps_python_language(client, sample_course, db_session):
    _first_code_practice(sample_course)["language"] = "python"
    course_id = client.post("/api/courses", json=sample_course).json()["id"]

    stored = db_session.get(CourseModel, course_id)
    assert _first_code_practice(stored.data)["language"] == "python"
    fetched = client.get(f"/api/courses/{course_id}").json()
    assert _first_code_practice(fetched)["language"] == "python"


def test_stored_course_without_language_reads_as_javascript(
    client, sample_course, db_session
):
    db_session.add(
        CourseModel(
            id=sample_course["id"],
            title=sample_course["title"],
            data=sample_course,
            owner_user_id=None,
        )
    )
    db_session.commit()

    fetched = client.get(f"/api/courses/{sample_course['id']}").json()
    assert _first_code_practice(fetched)["language"] == "javascript"


def test_create_course_rejects_unknown_language(client, sample_course):
    _first_code_practice(sample_course)["language"] = "ruby"
    response = client.post("/api/courses", json=sample_course)
    assert response.status_code == 422


def test_uploading_the_same_file_twice_forks_instead_of_conflicting(
    client, sample_course
):
    first = client.post("/api/courses", json=sample_course)
    second = client.post("/api/courses", json=sample_course)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_upload_keeps_forked_from_id_when_source_exists(client, sample_course):
    import copy

    original = client.post("/api/courses", json=sample_course).json()

    fork_payload = copy.deepcopy(sample_course)
    fork_payload["forkedFromId"] = original["id"]
    fork = client.post("/api/courses", json=fork_payload)

    assert fork.status_code == 201
    assert fork.json()["forkedFromId"] == original["id"]
    assert client.get(f"/api/courses/{fork.json()['id']}").json()[
        "forkedFromId"
    ] == original["id"]


def test_upload_drops_forked_from_id_pointing_at_nothing(client, sample_course):
    import copy

    payload = copy.deepcopy(sample_course)
    payload["forkedFromId"] = "does-not-exist"
    response = client.post("/api/courses", json=payload)

    assert response.status_code == 201
    assert response.json()["forkedFromId"] is None


def test_get_missing_course_is_404(client):
    response = client.get("/api/courses/does-not-exist")
    assert response.status_code == 404


def test_create_course_without_auth_is_rejected(client, sample_course):
    from app.auth import get_current_user
    from app.config import Settings, get_settings
    from app.main import app

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
    assert client.get("/api/courses").json() == {"items": [], "total": 0}


def test_search_matches_title_case_insensitively(client, sample_course):
    client.post("/api/courses", json=sample_course)

    assert client.get("/api/courses?q=test").json()["total"] == 1
    assert client.get("/api/courses?q=TEST").json()["total"] == 1
    assert client.get("/api/courses?q=nomatch").json()["total"] == 0


def test_update_tags_by_owner(client, sample_course):
    course_id = client.post("/api/courses", json=sample_course).json()["id"]

    response = client.patch(
        f"/api/courses/{course_id}/tags", json={"tags": ["python", "beginner"]}
    )
    assert response.status_code == 200
    assert response.json()["tags"] == ["beginner", "python"]

    fetched = client.get(f"/api/courses/{course_id}").json()
    assert fetched["tags"] == ["beginner", "python"]


def test_update_tags_dedupes_and_strips_blanks(client, sample_course):
    course_id = client.post("/api/courses", json=sample_course).json()["id"]

    response = client.patch(
        f"/api/courses/{course_id}/tags",
        json={"tags": ["python", "python", "  ", "beginner", " beginner "]},
    )
    assert response.json()["tags"] == ["beginner", "python"]


def test_update_tags_rejected_for_non_owner(client, sample_course):
    from app.auth import AuthenticatedUser, get_current_user
    from app.main import app

    course_id = client.post("/api/courses", json=sample_course).json()["id"]

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="user-2")
    try:
        response = client.patch(
            f"/api/courses/{course_id}/tags", json={"tags": ["python"]}
        )
    finally:
        app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
            id="user-1"
        )

    assert response.status_code == 403
    assert client.get(f"/api/courses/{course_id}").json()["tags"] == []


def test_update_tags_missing_course_is_404(client):
    response = client.patch(
        "/api/courses/does-not-exist/tags", json={"tags": ["python"]}
    )
    assert response.status_code == 404


def test_filter_by_owner(client, sample_course):
    from app.auth import AuthenticatedUser, get_current_user
    from app.main import app

    own = client.post("/api/courses", json=sample_course).json()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="user-2")
    try:
        others = client.post("/api/courses", json=sample_course).json()
    finally:
        app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
            id="user-1"
        )

    mine = client.get("/api/courses?owner_user_id=user-1").json()["items"]
    assert [c["id"] for c in mine] == [own["id"]]

    assert client.get("/api/courses").json()["total"] == 2
    assert others["id"] != own["id"]


def test_pagination_limits_and_offsets(client, sample_course):
    import copy

    for i in range(3):
        course = copy.deepcopy(sample_course)
        course["id"] = f"test-course-{i}"
        client.post("/api/courses", json=course)

    first_page = client.get("/api/courses?limit=2&offset=0").json()
    assert len(first_page["items"]) == 2
    assert first_page["total"] == 3

    second_page = client.get("/api/courses?limit=2&offset=2").json()
    assert len(second_page["items"]) == 1
    assert second_page["total"] == 3

    first_ids = {c["id"] for c in first_page["items"]}
    second_ids = {c["id"] for c in second_page["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_for_user_id_includes_owned_and_saved(client, sample_course):
    from app.auth import AuthenticatedUser, get_current_user, get_current_user_optional
    from app.main import app

    owned = client.post("/api/courses", json=sample_course).json()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="user-2")
    app.dependency_overrides[get_current_user_optional] = lambda: AuthenticatedUser(
        id="user-2"
    )
    try:
        others = client.post("/api/courses", json=sample_course).json()
    finally:
        app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
            id="user-1"
        )
        app.dependency_overrides[get_current_user_optional] = lambda: AuthenticatedUser(
            id="user-1"
        )

    # user-1 hasn't saved user-2's course yet - for_user_id=user-1 excludes it.
    mine = client.get("/api/courses?for_user_id=user-1").json()["items"]
    assert [c["id"] for c in mine] == [owned["id"]]

    save = client.post(f"/api/courses/{others['id']}/save")
    assert save.status_code == 204

    mine = client.get("/api/courses?for_user_id=user-1").json()["items"]
    assert {c["id"] for c in mine} == {owned["id"], others["id"]}
    saved_flags = {c["id"]: c["saved"] for c in client.get("/api/courses").json()["items"]}
    assert saved_flags[owned["id"]] is True
    assert saved_flags[others["id"]] is True


def test_save_is_idempotent(client, sample_course):
    from app.auth import AuthenticatedUser, get_current_user, get_current_user_optional
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="author")
    app.dependency_overrides[get_current_user_optional] = lambda: AuthenticatedUser(
        id="author"
    )
    course_id = client.post("/api/courses", json=sample_course).json()["id"]
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="user-1")
    app.dependency_overrides[get_current_user_optional] = lambda: AuthenticatedUser(
        id="user-1"
    )

    assert client.post(f"/api/courses/{course_id}/save").status_code == 204
    assert client.post(f"/api/courses/{course_id}/save").status_code == 204
    assert client.get("/api/courses?for_user_id=user-1").json()["total"] == 1


def test_unsave_is_idempotent_and_removes_membership(client, sample_course):
    from app.auth import AuthenticatedUser, get_current_user, get_current_user_optional
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="author")
    app.dependency_overrides[get_current_user_optional] = lambda: AuthenticatedUser(
        id="author"
    )
    course_id = client.post("/api/courses", json=sample_course).json()["id"]
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="user-1")
    app.dependency_overrides[get_current_user_optional] = lambda: AuthenticatedUser(
        id="user-1"
    )

    client.post(f"/api/courses/{course_id}/save")
    assert client.delete(f"/api/courses/{course_id}/save").status_code == 204
    assert client.delete(f"/api/courses/{course_id}/save").status_code == 204
    assert client.get("/api/courses?for_user_id=user-1").json()["total"] == 0


def test_owner_cannot_save_or_unsave_own_course(client, sample_course):
    course_id = client.post("/api/courses", json=sample_course).json()["id"]

    save = client.post(f"/api/courses/{course_id}/save")
    assert save.status_code == 400

    unsave = client.delete(f"/api/courses/{course_id}/save")
    assert unsave.status_code == 400


def test_save_missing_course_is_404(client):
    assert client.post("/api/courses/does-not-exist/save").status_code == 404
    assert client.delete("/api/courses/does-not-exist/save").status_code == 404


def test_filter_by_tag(client, sample_course):
    import copy

    course_a = sample_course
    course_b = copy.deepcopy(sample_course)
    course_b["id"] = "test-course-b"

    id_a = client.post("/api/courses", json=course_a).json()["id"]
    id_b = client.post("/api/courses", json=course_b).json()["id"]
    client.patch(f"/api/courses/{id_a}/tags", json={"tags": ["python"]})
    client.patch(f"/api/courses/{id_b}/tags", json={"tags": ["javascript"]})

    python_courses = client.get("/api/courses?tag=python").json()["items"]
    assert [c["id"] for c in python_courses] == [id_a]

    js_courses = client.get("/api/courses?tag=javascript").json()["items"]
    assert [c["id"] for c in js_courses] == [id_b]

    assert client.get("/api/courses").json()["total"] == 2
