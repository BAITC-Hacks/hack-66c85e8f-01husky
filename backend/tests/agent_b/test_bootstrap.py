import os
import subprocess
import sys
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.config import BACKEND_DIR, get_settings


def test_migrations_and_seed_on_percent_encoded_url(tmp_path):
    """Use real migrations, not metadata.create_all, including a second startup."""
    schema = f"bootstrap_{uuid4().hex}"
    database_url = get_settings().database_url
    setup = create_engine(database_url, isolation_level="AUTOCOMMIT")
    url = make_url(database_url).update_query_dict({"options": f"-csearch_path={schema}"})
    encoded_url = url.render_as_string(hide_password=False)
    assert "%" in encoded_url
    environment = {
        **os.environ,
        "DATABASE_URL": encoded_url,
        "DATA_DIR": str(tmp_path / "data"),
        "OUTBOX_DIR": str(tmp_path / "outbox"),
    }
    with setup.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        for _ in range(2):
            for module, args in [("alembic", ["upgrade", "head"]), ("app.seed", [])]:
                result = subprocess.run(
                    [sys.executable, "-m", module, *args],
                    cwd=BACKEND_DIR,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                assert result.returncode == 0, result.stdout + result.stderr
        with setup.connect() as connection:
            for table, expected in [("users", 1), ("participants", 5), ("directions", 7)]:
                count = connection.scalar(text(f'SELECT count(*) FROM "{schema}".{table}'))
                assert count == expected
    finally:
        with setup.connect() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        setup.dispose()
