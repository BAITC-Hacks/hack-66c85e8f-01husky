import pytest

from app.models import Meeting, Segment
from app.models.enums import MeetingSource


def test_admin_page_has_only_local_assets(client):
    response = client.get("/admin")
    assert response.status_code == 200
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"
    assert "/admin-assets/app.js" in response.text
    assert "admin123" not in response.text
    assert client.get("/admin-assets/app.js").status_code == 200
    assert client.get("/admin-assets/style.css").status_code == 200


@pytest.mark.parametrize("path", ["/tables", "/tables/users", "/tables/segments"])
def test_admin_requires_admin(client, user_client, path):
    assert client.get(f"/api/v1/admin{path}").status_code == 401
    assert user_client.get(f"/api/v1/admin{path}").status_code == 403


def test_admin_allowlist_and_counts(admin_client):
    response = admin_client.get("/api/v1/admin/tables")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    tables = {table["name"]: table for table in response.json()["tables"]}
    assert len(tables) == 9
    assert tables["users"]["count"] == 2
    for table, hidden in [
        ("users", "password_hash"),
        ("participants", "voice_embedding"),
        ("meetings", "audio_path"),
        ("meetings", "bot_url"),
    ]:
        assert hidden not in [column["name"] for column in tables[table]["columns"]]
        records = admin_client.get(f"/api/v1/admin/tables/{table}").json()["rows"]
        assert all(hidden not in row for row in records)
    assert admin_client.get("/api/v1/admin/tables/alembic_version").status_code == 404
    assert admin_client.get("/api/v1/admin/tables/pg_authid").status_code == 404


def test_search_pagination_and_validation(admin_client):
    response = admin_client.get("/api/v1/admin/tables/participants?limit=1&offset=1").json()
    assert response["total"] == 3 and len(response["rows"]) == 1
    assert response["rows"][0]["id"] == 2
    response = admin_client.get("/api/v1/admin/tables/participants", params={"q": "айбек"}).json()
    assert response["total"] == 1 and response["rows"][0]["id"] == 2
    for query in ["%", "_", "' OR 1=1 --"]:
        assert (
            admin_client.get("/api/v1/admin/tables/participants", params={"q": query}).json()[
                "total"
            ]
            == 0
        )
    for params in [
        {"limit": 101},
        {"offset": -1},
        {"meeting_id": 0},
        {"meeting_id": 1},
        {"q": "a" * 201},
    ]:
        assert admin_client.get("/api/v1/admin/tables/users", params=params).status_code == 422


def test_meeting_filter_transcript_order_and_untrusted_text(admin_client, db, seed):
    from datetime import date

    meetings = [
        Meeting(
            title=f"Test {i}",
            meeting_date=date(2026, 9, 23),
            source=MeetingSource.upload,
            created_by=seed["admin"].id,
        )
        for i in range(2)
    ]
    db.add_all(meetings)
    db.flush()
    untrusted = '<img src=x onerror="alert(1)">'
    for index in [2, 0, 1]:
        db.add(
            Segment(
                meeting_id=meetings[0].id,
                idx=index,
                start=index,
                end=index + 1,
                speaker="unknown",
                text=untrusted,
                lang="other",
            )
        )
    db.commit()
    response = admin_client.get(
        "/api/v1/admin/tables/segments", params={"meeting_id": meetings[0].id}
    )
    assert response.status_code == 200
    assert [row["idx"] for row in response.json()["rows"]] == [0, 1, 2]
    assert response.json()["rows"][0]["text"] == untrusted
    assert (
        admin_client.get(
            "/api/v1/admin/tables/segments", params={"meeting_id": meetings[1].id}
        ).json()["total"]
        == 0
    )
    assert (
        admin_client.get(
            "/api/v1/admin/tables/meetings", params={"meeting_id": meetings[0].id}
        ).json()["total"]
        == 1
    )


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_no_database_write_endpoints(admin_client, method):
    assert getattr(admin_client, method)("/api/v1/admin/tables/users").status_code == 405
