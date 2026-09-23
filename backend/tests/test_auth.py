from sqlalchemy import select

from app.models import Participant


def test_register_claims_guest_participant(client, seed, db) -> None:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "aibek@example.com", "password": "secret1", "name": "Айбек", "locale": "kk"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["role"] == "user" and body["locale"] == "kk"
    p = db.scalar(select(Participant).where(Participant.email == "aibek@example.com"))
    assert p.user_id == body["id"]
    assert body["participant_id"] == p.id
    assert "access_token" in client.cookies


def test_register_creates_participant_when_none(client, seed, db) -> None:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "secret1", "name": "Новый"},
    )
    assert r.status_code == 201
    p = db.scalar(select(Participant).where(Participant.email == "new@example.com"))
    assert p and p.user_id == r.json()["id"]


def test_register_duplicate(client, seed) -> None:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "ADMIN@example.com", "password": "secret1", "name": "x"},
    )
    assert r.status_code == 409


def test_login_me_logout(client, seed) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    r = client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin123"}
    )
    assert r.status_code == 200 and r.json()["role"] == "admin"
    assert client.get("/api/v1/auth/me").json()["email"] == "admin@example.com"
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_login_wrong_password(client, seed) -> None:
    r = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "nope"})
    assert r.status_code == 401
