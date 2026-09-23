import os

os.environ["PIPELINE_FAKE"] = "1"
os.environ["DATABASE_URL"] = "postgresql+psycopg://protocol:protocol@localhost:5432/protocol_test"
os.environ["SECRET_KEY"] = "test-secret"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Direction, Participant, User
from app.models.enums import UserRole
from app.security import hash_password


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture(autouse=True)
def db():
    with SessionLocal() as s:
        tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
        s.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        s.commit()
        yield s


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def seed(db):
    admin = User(
        email="admin@example.com",
        password_hash=hash_password("admin123"),
        name="Admin",
        role=UserRole.admin,
    )
    user = User(email="user@example.com", password_hash=hash_password("user123"), name="User")
    db.add_all([admin, user])
    db.add_all(Direction(name=n) for n in ["Финансы", "ИТ", "Юридическое", "Другое"])
    db.add_all(
        [
            Participant(name="Серик Нурланов", email="serik@example.com", position="Директор"),
            Participant(name="Айбек Сериков", email="aibek@example.com", position="Финансист"),
            Participant(name="Дана Ахметова", email="user@example.com", position="Юрист"),
        ]
    )
    db.commit()
    return {"admin": admin, "user": user}


def login(client: TestClient, email: str, password: str) -> None:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text


@pytest.fixture
def admin_client(client, seed):
    login(client, "admin@example.com", "admin123")
    return client


@pytest.fixture
def user_client(client, seed):
    login(client, "user@example.com", "user123")
    return client
