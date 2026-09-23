import logging
import os
import tempfile
from pathlib import Path

import pytest

from bots import cli
from bots.base import BotConfig, child_environment


def args():
    return [
        "--platform",
        "meet",
        "--url",
        "https://meet.google.com/abc-defg-hij",
        "--meeting-id",
        "1",
        "--api-url",
        "http://api/api/v1",
    ]


def test_help_lists_platforms(capsys):
    with pytest.raises(SystemExit) as error:
        cli.main(["--help"])
    assert error.value.code == 0
    assert "teams" in capsys.readouterr().out


def test_missing_token_fails_before_browser(monkeypatch):
    monkeypatch.delenv("KENES_BOT_UPLOAD_TOKEN", raising=False)
    assert cli.main(args()) == 1


def test_cli_env_flags_and_no_sensitive_logs(monkeypatch, caplog):
    monkeypatch.setenv("KENES_BOT_UPLOAD_TOKEN", "private-token")
    seen = []

    class Fake:
        def run(self):
            raise RuntimeError("private-token https://secret-url/")

    def build(cfg):
        seen.append(cfg)
        return Fake()

    monkeypatch.setattr(cli, "build", build)
    with caplog.at_level(logging.INFO):
        assert (
            cli.main(
                args()
                + [
                    "--max-duration-sec",
                    "12",
                    "--lobby-timeout-sec",
                    "8",
                    "--upload-timeout-sec",
                    "2",
                ]
            )
            == 1
        )
    assert seen[0].max_duration_sec == 12
    assert seen[0].lobby_timeout_sec == 8
    assert seen[0].upload_timeout_sec == 2
    assert seen[0].api_token == "private-token"
    assert "KENES_BOT_UPLOAD_TOKEN" not in os.environ
    assert "private-token" not in caplog.text
    assert "secret-url" not in caplog.text
    assert "private-token" not in repr(seen[0])


def test_environment_strips_credentials(monkeypatch):
    monkeypatch.setenv("KENES_BOT_UPLOAD_TOKEN", "secret")
    monkeypatch.setenv("KENES_BOT_MEETING_URL", "https://meet.google.com/abc-defg-hij")
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret")
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setenv("PULSE_SERVER", "unix:/tmp/pulse/native")
    env = child_environment()
    assert not any(
        key in env
        for key in (
            "KENES_BOT_UPLOAD_TOKEN",
            "KENES_BOT_MEETING_URL",
            "DATABASE_URL",
            "OPENAI_API_KEY",
        )
    )
    assert env["PULSE_SERVER"] == "unix:/tmp/pulse/native"


def test_token_argv_removed():
    with pytest.raises(SystemExit):
        cli.main(args() + ["--api-token", "secret"])


def test_defaults():
    assert BotConfig("meet", "private", 1, "private", "secret").display_name == "Kenes AI"
    assert (
        BotConfig("meet", "private", 1, "private", "secret").out_dir
        == Path(tempfile.gettempdir()) / "kenes-recordings"
    )


def test_url_from_env_is_consumed_before_build(monkeypatch, caplog):
    invitation = "https://meet.google.com/abc-defg-hij?secret=invitation"
    monkeypatch.setenv("KENES_BOT_MEETING_URL", invitation)
    monkeypatch.setenv("KENES_BOT_UPLOAD_TOKEN", "secret-token")
    seen = []

    class Fake:
        def run(self):
            return {"status": "uploaded"}

    def build(cfg):
        assert "KENES_BOT_MEETING_URL" not in os.environ
        assert "KENES_BOT_UPLOAD_TOKEN" not in os.environ
        seen.append(cfg)
        return Fake()

    monkeypatch.setattr(cli, "build", build)
    argv = args()
    del argv[2:4]
    with caplog.at_level(logging.INFO):
        assert cli.main(argv) == 0
    assert seen[0].url == invitation
    assert invitation not in caplog.text
    assert invitation not in repr(seen[0])


def test_missing_url_is_static_failure(monkeypatch, caplog):
    monkeypatch.setenv("KENES_BOT_UPLOAD_TOKEN", "secret-token")
    monkeypatch.delenv("KENES_BOT_MEETING_URL", raising=False)
    argv = args()
    del argv[2:4]
    assert cli.main(argv) == 1
    assert "Meeting invitation URL is invalid" in caplog.text
