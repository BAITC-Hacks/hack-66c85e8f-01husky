import signal
import subprocess
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Meeting
from app.models.enums import MeetingStatus
from app.services.bot_tokens import valid_bot_upload_token
from app.tasks import run_bot as worker
from app.tasks.celery_app import celery_app
from tests.agent_b.test_bot_security import bot_meeting


@pytest.fixture
def pending(admin_client, _schema, monkeypatch):
    monkeypatch.setattr(worker, "SessionLocal", lambda: Session(_schema))
    monkeypatch.setattr(worker.run_bot, "delay", lambda *args: None)
    return bot_meeting(admin_client)


@pytest.fixture
def process(monkeypatch):
    process = Mock(pid=98765)
    process.wait.return_value = 0
    monkeypatch.setattr(worker.subprocess, "Popen", Mock(return_value=process))
    monkeypatch.setattr(worker.os, "killpg", Mock())
    return process


def test_worker_routes_to_dedicated_queue():
    assert celery_app.conf.task_routes[worker.run_bot.name] == {"queue": "bots"}


def test_worker_scopes_env_and_budgets_time(pending, db, process, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "never-pass-this")
    monkeypatch.setenv("DATABASE_URL", "never-pass-this-either")
    worker.run_bot.run(pending)
    args, kwargs = worker.subprocess.Popen.call_args
    assert "--headed" in args[0]
    assert "--api-token" not in args[0]
    assert "--url" not in args[0]
    assert "https://meet.google.com/abc-defg-hij" not in args[0]
    assert args[0][args[0].index("--out-dir") + 1] == "/tmp/kenes-recordings"
    env = kwargs["env"]
    assert valid_bot_upload_token(env["KENES_BOT_UPLOAD_TOKEN"], pending)
    assert env["KENES_BOT_MEETING_URL"] == "https://meet.google.com/abc-defg-hij"
    assert "SECRET_KEY" not in env and "DATABASE_URL" not in env
    assert kwargs["start_new_session"] is True
    assert args[0][args[0].index("--audio-device") + 1] == "pulse:kenes.monitor"
    assert "--lobby-timeout-sec" in args[0]
    assert args[0][args[0].index("--max-duration-sec") + 1] == "7200"
    assert args[0][args[0].index("--upload-timeout-sec") + 1] == "120"
    db.expire_all()
    assert db.get(Meeting, pending).status == MeetingStatus.failed
    assert "without uploading" in db.get(Meeting, pending).error


def test_worker_timeout_terminates_whole_group(pending, db, process):
    process.wait.side_effect = [subprocess.TimeoutExpired("bot", 1), None, None]
    worker.run_bot.run(pending)
    worker.os.killpg.assert_any_call(process.pid, signal.SIGTERM)
    worker.os.killpg.assert_any_call(process.pid, signal.SIGKILL)
    db.expire_all()
    assert db.get(Meeting, pending).error == "Meeting bot timed out"


@pytest.mark.parametrize("returncode", [0, 1])
def test_callback_success_cannot_be_overwritten(pending, db, process, _schema, returncode):
    def accepted_callback(*args, **kwargs):
        with Session(_schema) as session:
            meeting = session.get(Meeting, pending)
            meeting.audio_path = "/data/audio/accepted.wav"
            meeting.status, meeting.progress_stage = MeetingStatus.processing, "transcribing"
            session.commit()
        return returncode

    process.wait.side_effect = accepted_callback
    worker.run_bot.run(pending)
    db.expire_all()
    meeting = db.get(Meeting, pending)
    assert meeting.status == MeetingStatus.processing
    assert meeting.progress_stage == "transcribing"
    assert meeting.error is None


def test_duplicate_delivery_does_not_launch_second_bot(pending, db, process):
    meeting = db.get(Meeting, pending)
    meeting.progress_stage = "bot_recording"
    db.commit()
    worker.run_bot.run(pending)
    worker.subprocess.Popen.assert_not_called()


def test_bad_budget_does_not_launch_bot(pending, db, process, monkeypatch):
    monkeypatch.setattr(get_settings(), "bot_timeout_sec", 60)
    worker.run_bot.run(pending)
    worker.subprocess.Popen.assert_not_called()
    db.expire_all()
    assert db.get(Meeting, pending).status == MeetingStatus.failed


def test_runtime_start_failure(pending, db, process):
    worker.subprocess.Popen.side_effect = FileNotFoundError()
    worker.run_bot.run(pending)
    db.expire_all()
    assert db.get(Meeting, pending).error == "Cannot start meeting bot runtime"


def test_default_secret_fails_without_starting_bot(pending, db, process, monkeypatch):
    monkeypatch.setattr(get_settings(), "secret_key", "change-me-in-env")
    worker.run_bot.run(pending)
    worker.subprocess.Popen.assert_not_called()
    db.expire_all()
    meeting = db.get(Meeting, pending)
    assert meeting.status == MeetingStatus.failed
    assert "non-default SECRET_KEY" in meeting.error
