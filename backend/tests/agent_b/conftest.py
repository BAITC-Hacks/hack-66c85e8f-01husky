"""Isolate B's integration checks from A's concurrent tests in the same database."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Base, get_db
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _schema():
    schema = f"agent_b_{uuid4().hex}"
    url = get_settings().database_url
    setup = create_engine(url, isolation_level="AUTOCOMMIT")
    with setup.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        Base.metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()
        with setup.connect() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        setup.dispose()


@pytest.fixture(autouse=True)
def db(_schema, tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    monkeypatch.setattr(settings, "outbox_dir", tmp_path / "outbox")
    with Session(_schema, expire_on_commit=False) as session:
        tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
        session.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        session.commit()

        def override():
            yield session

        previous = app.dependency_overrides.get(get_db)
        app.dependency_overrides[get_db] = override
        try:
            yield session
        finally:
            if previous is None:
                app.dependency_overrides.pop(get_db, None)
            else:
                app.dependency_overrides[get_db] = previous
