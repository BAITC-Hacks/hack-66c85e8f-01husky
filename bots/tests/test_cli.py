import pytest

from bots import cli
from bots.base import BotConfig, MeetingBot


def test_help_lists_platforms(capsys) -> None:
    with pytest.raises(SystemExit) as e:
        cli.main(["--help"])
    assert e.value.code == 0
    assert "meet" in capsys.readouterr().out


def test_unimplemented_adapter_exits_2() -> None:
    code = cli.main(
        [
            "--platform",
            "meet",
            "--url",
            "https://meet.google.com/x",
            "--meeting-id",
            "1",
            "--api-url",
            "http://localhost:8000/api/v1",
            "--api-token",
            "t",
        ]
    )
    assert code == 2


def test_run_lifecycle_and_upload(monkeypatch, tmp_path) -> None:
    calls: list[str] = []

    class Fake(MeetingBot):
        def join(self):
            calls.append("join")

        def wait_admitted(self, timeout_sec=600):
            calls.append("admitted")

        def call_ended(self):
            return True

        def leave(self):
            calls.append("leave")

        def start_recording(self):
            self.audio_path.parent.mkdir(parents=True, exist_ok=True)
            self.audio_path.write_bytes(b"RIFF")
            calls.append("rec")

        def stop_recording(self):
            calls.append("stop")

    posted = {}

    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"id": 7, "status": "uploaded"}

    def fake_post(url, files, headers, timeout):
        posted.update(url=url, token=headers["X-Bot-Token"])
        return R()

    monkeypatch.setattr("bots.base.httpx.post", fake_post)
    cfg = BotConfig(
        "meet", "https://meet.google.com/x", 7, "http://api/api/v1", "tok", out_dir=tmp_path
    )
    assert Fake(cfg).run() == {"id": 7, "status": "uploaded"}
    assert calls == ["join", "admitted", "rec", "stop", "leave"]
    assert posted == {"url": "http://api/api/v1/meetings/7/audio", "token": "tok"}
