import os

os.environ.setdefault("PIPELINE_FAKE", "1")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://protocol:protocol@localhost:5432/protocol_test"
)

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
