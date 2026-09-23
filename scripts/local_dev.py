"""Local macOS stack. Run with backend/.venv/bin/python scripts/local_dev.py COMMAND.

Requires brew install postgresql@16 redis ffmpeg, and uv sync --project backend --extra stt.
Own cluster, private .env, persistent data; never removes databases or audio.
"""

import argparse
import json
import os
import secrets
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import psycopg
from dotenv import dotenv_values
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
STATE = BACKEND / "data" / "local"
PG = (
    Path(
        subprocess.check_output(
            ["brew", "--prefix", "postgresql@16"], text=True
        ).strip()
    )
    / "bin"
)
ENV = ROOT / ".env"


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def require_free(port):
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError(
                f"Port {port} is occupied by another process; stop it first"
            )


def configuration():
    if not ENV.exists() or dotenv_values(ENV).get("HACKALEM_LOCAL_SETUP") != "1":
        raise RuntimeError(
            "Run setup first; existing unmanaged .env is never overwritten"
        )
    return {k: v for k, v in dotenv_values(ENV).items() if v is not None}


def setup():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    if ENV.exists():
        configuration()
    else:
        password = secrets.token_hex(24)
        values = {
            "HACKALEM_LOCAL_SETUP": "1",
            "DATABASE_URL": f"postgresql+psycopg://protocol:{password}@127.0.0.1:5432/protocol",
            "TEST_DATABASE_URL": f"postgresql+psycopg://protocol:{password}@127.0.0.1:5432/protocol_test",
            "REDIS_URL": f"redis://:{secrets.token_hex(24)}@127.0.0.1:6379/0",
            "SECRET_KEY": secrets.token_hex(32),
            "BOT_API_TOKEN": secrets.token_hex(32),
            "PIPELINE_FAKE": "0",
            "STT_BACKEND": "local",
            "STT_MODEL": "large-v3-turbo",
            "STT_MODEL_DIR": str(ROOT / "pipeline" / ".models"),
            "STT_LANGUAGE": "auto",
            "STT_DEVICE": "cpu",
            "STT_COMPUTE_TYPE": "int8",
            "STT_CPU_THREADS": "4",
            "DIARIZATION_CPU_THREADS": "4",
            "DIARIZATION_THRESHOLD": "0.5",
            "HF_HUB_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "LLM_PROVIDER": "ollama",
            "OLLAMA_URL": "http://127.0.0.1:11434",
            "DATA_DIR": str(BACKEND / "data"),
            "OUTBOX_DIR": str(BACKEND / "outbox"),
            "CORS_ORIGINS": json.dumps(
                [
                    f"http://{host}:{port}"
                    for host in ("localhost", "127.0.0.1")
                    for port in (3000, 5173)
                ]
            ),
            "COOKIE_SECURE": "false",
            "DEBUG": "false",
            "PUBLIC_API_URL": "http://localhost:8000/api/v1",
        }
        with open(ENV, "x", opener=lambda p, flags: os.open(p, flags, 0o600)) as f:
            f.write("\n".join(f"{k}='{v}'" for k, v in values.items()) + "\n")
    start_databases()
    env = {**os.environ, **configuration()}
    run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env)
    run([sys.executable, "-m", "app.seed"], cwd=BACKEND, env=env)
    print("Local configuration and databases ready. Credentials are in ignored .env.")


def start_databases():
    from urllib.parse import urlparse

    cfg = configuration()
    cluster = STATE / "postgres"
    sockets = STATE / "sockets"
    sockets.mkdir(parents=True, exist_ok=True)
    if not (cluster / "PG_VERSION").exists():
        run(
            [
                PG / "initdb",
                "-D",
                cluster,
                "--encoding=UTF8",
                "--locale=en_US.UTF-8",
                "--auth-local=peer",
                "--auth-host=scram-sha-256",
            ]
        )
    status = subprocess.run(
        [str(PG / "pg_ctl"), "-D", str(cluster), "status"],
        capture_output=True,
        check=False,
    )
    if status.returncode:
        require_free(5432)
        options = shlex.join(["-h", "127.0.0.1", "-p", "5432", "-k", str(sockets)])
        run(
            [
                PG / "pg_ctl",
                "-D",
                cluster,
                "-l",
                STATE / "postgres.log",
                "-o",
                options,
                "-w",
                "start",
            ]
        )
    password = urlparse(cfg["DATABASE_URL"]).password
    with psycopg.connect(dbname="postgres", host=str(sockets), autocommit=True) as db:
        if not db.execute("SELECT 1 FROM pg_roles WHERE rolname='protocol'").fetchone():
            db.execute(
                sql.SQL("CREATE ROLE protocol LOGIN PASSWORD {}").format(
                    sql.Literal(password)
                )
            )
        for name in ("protocol", "protocol_test"):
            if not db.execute(
                "SELECT 1 FROM pg_database WHERE datname=%s", (name,)
            ).fetchone():
                db.execute(
                    sql.SQL("CREATE DATABASE {} OWNER protocol").format(
                        sql.Identifier(name)
                    )
                )

    import redis

    client = redis.Redis.from_url(cfg["REDIS_URL"])
    try:
        client.ping()
    except redis.exceptions.ConnectionError:
        require_free(6379)
        redis_config = STATE / "redis.conf"
        redis_config.write_text(
            "bind 127.0.0.1\nport 6379\nprotected-mode yes\ndaemonize yes\nappendonly yes\n"
            f"requirepass {urlparse(cfg['REDIS_URL']).password}\n"
            f'dir "{STATE}"\npidfile "{STATE / "redis.pid"}"\n'
            f'logfile "{STATE / "redis.log"}"\n'
        )
        redis_config.chmod(0o600)
        run([shutil.which("redis-server"), redis_config])
        for _ in range(50):
            try:
                if client.ping():
                    break
            except redis.exceptions.ConnectionError:
                time.sleep(0.1)
        else:
            raise RuntimeError("Redis startup failed")


def live_pid(name):
    path = STATE / f"{name}.pid"
    if not path.exists():
        return None
    pid = int(path.read_text())
    command = subprocess.run(
        ["ps", "-p", str(pid), "-o", "command="],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    marker = (
        "uvicorn app.main:app"
        if name == "api"
        else f"celery -A app.tasks.celery_app:celery_app {name}"
    )
    cwd = subprocess.run(
        ["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.splitlines()
    return pid if f"n{BACKEND}" in cwd and marker in command else None


def start():
    start_databases()
    env = {**os.environ, **configuration()}
    commands = {
        "worker": [
            "celery",
            "-A",
            "app.tasks.celery_app:celery_app",
            "worker",
            "--pool=solo",
            "--concurrency=1",
            "--loglevel=info",
        ],
        "beat": [
            "celery",
            "-A",
            "app.tasks.celery_app:celery_app",
            "beat",
            "--loglevel=info",
            "--schedule",
            str(STATE / "celerybeat-schedule"),
        ],
        "api": ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    }
    if not live_pid("api"):
        require_free(8000)
    for name, args in commands.items():
        if live_pid(name):
            continue
        with (STATE / f"{name}.log").open("a") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", *args],
                cwd=BACKEND,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
        (STATE / f"{name}.pid").write_text(str(process.pid))
    for _ in range(100):
        try:
            with urlopen("http://127.0.0.1:8000/api/v1/health", timeout=1) as response:
                print(response.read().decode())
            if not live_pid("worker") or not live_pid("beat"):
                raise RuntimeError("Worker/beat exited; see logs in backend/data/local")
            print("API ready: http://localhost:8000/docs")
            return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError("API startup timed out; see backend/data/local/api.log")


def stop():
    # Stop only this project's app processes. PostgreSQL/Redis and all data are retained.
    for name in ("api", "beat", "worker"):
        if pid := live_pid(name):
            os.kill(pid, signal.SIGTERM)
            print(f"Stopping {name} ({pid})")
    print("PostgreSQL/Redis remain running; data retained.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("setup", "start", "stop", "status"))
    command = parser.parse_args().command
    if command == "status":
        print({name: live_pid(name) for name in ("api", "worker", "beat")})
    else:
        {"setup": setup, "start": start, "stop": stop}[command]()
