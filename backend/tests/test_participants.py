import io


def test_list_requires_auth(client, seed) -> None:
    assert client.get("/api/v1/participants").status_code == 401


def test_create_guest_and_list(user_client) -> None:
    r = user_client.post(
        "/api/v1/participants", json={"name": "Гость Гостев", "email": "Guest@Example.com"}
    )
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "guest@example.com" and r.json()["user_id"] is None
    assert r.json()["has_voiceprint"] is False
    names = [p["name"] for p in user_client.get("/api/v1/participants").json()]
    assert "Гость Гостев" in names
    assert (
        user_client.post(
            "/api/v1/participants", json={"name": "x", "email": "guest@example.com"}
        ).status_code
        == 409
    )


def test_create_links_existing_user(admin_client, seed) -> None:
    r = admin_client.post(
        "/api/v1/participants", json={"name": "Админ", "email": "new-admin@example.com"}
    )
    assert r.json()["user_id"] is None
    admin_client.post(
        "/api/v1/auth/register", json={"email": "z@example.com", "password": "secret1", "name": "Z"}
    )


def test_voiceprint_roundtrip(admin_client) -> None:
    pid = admin_client.get("/api/v1/participants").json()[0]["id"]
    r = admin_client.post(
        f"/api/v1/participants/{pid}/voiceprint",
        files={"file": ("sample.webm", io.BytesIO(b"\x00" * 100), "audio/webm")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["embedding_dim"] == 192
    assert next(p for p in admin_client.get("/api/v1/participants").json() if p["id"] == pid)[
        "has_voiceprint"
    ]
    assert admin_client.delete(f"/api/v1/participants/{pid}/voiceprint").status_code == 204
    assert not next(p for p in admin_client.get("/api/v1/participants").json() if p["id"] == pid)[
        "has_voiceprint"
    ]


def test_user_cannot_touch_others_voiceprint(user_client) -> None:
    ps = user_client.get("/api/v1/participants").json()
    other = next(p for p in ps if p["email"] != "user@example.com")
    mine = next(p for p in ps if p["email"] == "user@example.com")
    assert user_client.delete(f"/api/v1/participants/{other['id']}/voiceprint").status_code == 403
    assert (
        user_client.patch(
            f"/api/v1/participants/{mine['id']}", json={"position": "Старший юрист"}
        ).status_code
        == 200
    )
    assert user_client.delete(f"/api/v1/participants/{other['id']}").status_code == 403


def test_directions_admin_only(user_client, admin_client) -> None:
    assert user_client.post("/api/v1/directions", json={"name": "Логистика"}).status_code == 403
    r = admin_client.post("/api/v1/directions", json={"name": "Логистика"})
    assert r.status_code == 201
    did = r.json()["id"]
    assert (
        admin_client.patch(f"/api/v1/directions/{did}", json={"is_active": False}).status_code
        == 200
    )
    active = [d["name"] for d in user_client.get("/api/v1/directions").json()]
    assert "Логистика" not in active
    all_ = [d["name"] for d in admin_client.get("/api/v1/directions?include_inactive=1").json()]
    assert "Логистика" in all_
