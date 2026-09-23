"""Run a real HTTP/curl workflow on a disposable schema in a *_test PostgreSQL DB.

Usage: uv run --project backend python backend/scripts/smoke_backend.py
Requires PostgreSQL, curl, ffmpeg and soffice. Uses PIPELINE_FAKE and inline Celery.
"""

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACKEND = Path(__file__).resolve().parents[1]


def exercise_api(api: str, work: Path) -> dict:
    """Create synthetic test data in the explicitly supplied development API."""
    cookie = str(work / "cookie")

    def curl(path, *args):
        result = subprocess.run(
            [
                "curl",
                "-sS",
                "--fail-with-body",
                "-b",
                cookie,
                "-c",
                cookie,
                *args,
                api + path,
            ],
            capture_output=True,
            check=False,
            timeout=150,
        )
        if result.returncode:
            raise RuntimeError(f"{path}: {result.stdout.decode(errors='replace')}")
        return result.stdout

    def request(path, body, method="POST"):
        return json.loads(
            curl(
                path,
                "-X",
                method,
                "-H",
                "Content-Type: application/json",
                "-d",
                json.dumps(body, ensure_ascii=False),
            )
        )

    user = request(
        "/auth/register",
        {
            "email": f"smoke-{uuid4().hex}@example.com",
            "password": "smoke-test-pass",
            "name": "Дана",
        },
    )
    chair = request("/participants", {"name": "Серик"})
    aibek = request("/participants", {"name": "Айбек"})
    audio = work / "fixture.wav"
    with wave.open(str(audio), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * 16000)
    meeting = json.loads(
        curl(
            "/meetings",
            "-F",
            "title=Проверка полного сценария",
            "-F",
            "meeting_date=2026-09-23",
            "-F",
            f"participant_ids={user['participant_id']}",
            "-F",
            f"participant_ids={chair['id']}",
            "-F",
            f"participant_ids={aibek['id']}",
            "-F",
            f"file=@{audio}",
        )
    )
    mid = meeting["id"]
    for _ in range(120):
        detail = json.loads(curl(f"/meetings/{mid}"))
        if detail["status"] in {"draft", "failed"}:
            break
        time.sleep(0.5)
    assert detail["status"] == "draft", detail
    assert len(detail["tasks"]) == 4
    request(
        f"/meetings/{mid}/speakers",
        [
            {"speaker": "SPEAKER_00", "participant_id": chair["id"]},
            {"speaker": "SPEAKER_01", "participant_id": user["participant_id"]},
        ],
        "PUT",
    )
    confirmed = request(f"/meetings/{mid}/confirm", {})
    assert confirmed["status"] == "confirmed"
    tasks = json.loads(curl("/tasks?mine=1"))
    assert tasks
    tid = tasks[0]["id"]
    request(f"/tasks/{tid}", {"status": "in_progress"}, "PATCH")
    done = request(f"/tasks/{tid}", {"status": "done"}, "PATCH")
    assert done["status"] == "done"
    notifications = json.loads(curl("/notifications?unread=1"))
    assert {"assigned", "protocol_ready"} <= {n["kind"] for n in notifications}
    request("/notifications/read-all", {})
    assert json.loads(curl("/notifications?unread=1")) == []
    docx = curl(f"/meetings/{mid}/export?format=docx&lang=kk")
    pdf = curl(f"/meetings/{mid}/export?format=pdf&lang=ru")
    assert docx.startswith(b"PK") and pdf.startswith(b"%PDF-")
    sed = request(f"/meetings/{mid}/sed", {})
    assert sed == request(f"/meetings/{mid}/sed", {})
    curl(f"/meetings/{mid}/audio", "-X", "DELETE")
    retained = json.loads(curl(f"/meetings/{mid}"))
    assert retained["audio_path"] is None and retained["segments"]
    return {
        "status": "passed",
        "tasks": len(detail["tasks"]),
        "notifications": len(notifications),
        "docx_bytes": len(docx),
        "pdf_bytes": len(pdf),
        "sed_ref": sed["sed_ref"],
    }


def run(database_url: str) -> dict:
    url = make_url(database_url)
    if not url.database or not url.database.endswith("_test"):
        raise ValueError("Smoke workflow requires a database whose name ends in _test")
    for executable in ("curl", "ffmpeg", "soffice"):
        if not shutil.which(executable):
            raise RuntimeError(f"Required executable missing: {executable}")
    schema = f"smoke_{uuid4().hex}"
    setup = create_engine(url, isolation_level="AUTOCOMMIT")
    with setup.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    server = None
    try:
        with tempfile.TemporaryDirectory(prefix="hackalem-smoke-") as directory:
            work = Path(directory)
            env = {
                **os.environ,
                "DATABASE_URL": url.update_query_dict(
                    {"options": f"-csearch_path={schema}"}
                ).render_as_string(hide_password=False),
                "DATA_DIR": str(work / "data"),
                "OUTBOX_DIR": str(work / "outbox"),
                "SECRET_KEY": uuid4().hex,
                "PIPELINE_FAKE": "1",
                "CELERY_EAGER": "1",
                "COOKIE_SECURE": "false",
            }
            for module, args in [("alembic", ["upgrade", "head"]), ("app.seed", [])]:
                subprocess.run(
                    [sys.executable, "-m", module, *args],
                    cwd=BACKEND,
                    env=env,
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            api = f"http://127.0.0.1:{port}/api/v1"
            with (work / "server.log").open("w") as log:
                server = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "app.main:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(port),
                    ],
                    cwd=BACKEND,
                    env=env,
                    stdout=log,
                    stderr=log,
                )
                try:
                    for _ in range(100):
                        ready = subprocess.run(
                            ["curl", "-s", "--fail", api + "/health"],
                            capture_output=True,
                            check=False,
                            timeout=5,
                        )
                        if ready.returncode == 0:
                            break
                        if server.poll() is not None:
                            raise RuntimeError((work / "server.log").read_text())
                        time.sleep(0.1)
                    else:
                        raise RuntimeError("API did not start")

                    return exercise_api(api, work)
                finally:
                    server.terminate()
                    server.wait(timeout=10)
    finally:
        with setup.connect() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        setup.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.getenv(
            "TEST_DATABASE_URL",
            "postgresql+psycopg://protocol:protocol@localhost:5432/protocol_test",
        ),
    )
    parser.add_argument(
        "--api-url", help="Existing dev API /api/v1 URL; creates synthetic test data"
    )
    args = parser.parse_args()
    if args.api_url:
        with tempfile.TemporaryDirectory(prefix="hackalem-smoke-http-") as directory:
            result = exercise_api(args.api_url.rstrip("/"), Path(directory))
    else:
        result = run(args.database_url)
    print(json.dumps(result, ensure_ascii=False))
