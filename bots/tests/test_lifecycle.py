import struct
import subprocess
import wave

import pytest

from bots.base import BotConfig, BotError, MeetingBot


def wav(path, silent=False):
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(struct.pack("<h", 0 if silent else 2000) * 32000)


class Fake(MeetingBot):
    fail = None

    def __init__(self, cfg):
        super().__init__(cfg)
        self.calls = []

    def stage(self, stage):
        self.calls.append(stage)
        if stage == self.fail:
            raise BotError("fixture failure")

    def join(self):
        self.stage("join")

    def wait_admitted(self, timeout_sec=600):
        self.stage("admit")

    def start_recording(self):
        self.stage("start")
        wav(self.audio_path)

    def record_until_end(self, poll_sec=1):
        self.stage("record")

    def call_ended(self):
        return True

    def stop_recording(self):
        self.stage("stop")

    def leave(self):
        self.stage("leave")

    def upload(self):
        self.stage("upload")
        return {"status": "uploaded"}


def config(tmp_path):
    return BotConfig(
        "meet",
        "https://meet.google.com/abc-defg-hij",
        7,
        "http://api/api/v1",
        "secret",
        out_dir=tmp_path,
    )


def test_lifecycle_and_cleanup(tmp_path):
    bot = Fake(config(tmp_path))
    assert bot.run() == {"status": "uploaded"}
    assert bot.calls == ["join", "admit", "start", "record", "stop", "stop", "leave", "upload"]
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("stage", ["join", "admit", "start", "record", "stop", "leave", "upload"])
def test_every_failure_cleans_tempdir(tmp_path, stage):
    bot = Fake(config(tmp_path))
    bot.fail = stage
    with pytest.raises(BotError):
        bot.run()
    assert "leave" in bot.calls
    assert list(tmp_path.iterdir()) == []
    if stage != "upload":
        assert "upload" not in bot.calls


@pytest.mark.parametrize("kind", ["silence", "invalid", "short", "truncated"])
def test_invalid_audio_not_uploaded(tmp_path, kind):
    bot = Fake(config(tmp_path))
    bot.audio_path = tmp_path / "bad.wav"
    wav(bot.audio_path, silent=kind == "silence")
    if kind == "invalid":
        bot.audio_path.write_bytes(b"RIFF broken")
    if kind == "short":
        with wave.open(str(bot.audio_path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b"\0\0")
    if kind == "truncated":
        bot.audio_path.write_bytes(bot.audio_path.read_bytes()[:1000])
    with pytest.raises(BotError):
        bot.validate_audio()


def test_dead_recorder_fails(tmp_path):
    bot = Fake(config(tmp_path))
    bot._ffmpeg = type("Dead", (), {"poll": lambda self: 1})()
    with pytest.raises(BotError, match="stopped unexpectedly"):
        MeetingBot.record_until_end(bot, poll_sec=0)


def test_recorder_timeout_kills_process(tmp_path):
    class Process:
        pid = 123
        calls = 0

        def send_signal(self, sig):
            killed.append(self.pid)

        def kill(self):
            killed.append(self.pid)

        def poll(self):
            return None

        def wait(self, timeout):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("ffmpeg", timeout)

    bot = Fake(config(tmp_path))
    process = Process()
    bot._ffmpeg = process
    killed = []
    with pytest.raises(BotError, match="stop cleanly"):
        MeetingBot.stop_recording(bot)
    assert killed == [123, 123]
    assert process.calls == 2
    assert bot._ffmpeg is None


def test_upload_does_not_follow_redirect_or_leak_response(tmp_path, monkeypatch):
    import httpx

    bot = Fake(config(tmp_path))
    bot.audio_path = tmp_path / "audio.wav"
    wav(bot.audio_path)
    seen = {}

    def post(url, **kwargs):
        seen.update(kwargs)
        return httpx.Response(
            302, headers={"location": "https://evil.example"}, request=httpx.Request("POST", url)
        )

    monkeypatch.setattr("bots.base.httpx.post", post)
    with pytest.raises(BotError, match="upload failed"):
        MeetingBot.upload(bot)
    assert seen["follow_redirects"] is False
    assert seen["headers"] == {"X-Bot-Token": "secret"}


def test_recording_root_is_created_private(tmp_path):
    cfg = config(tmp_path / "private-recordings")
    bot = Fake(cfg)
    bot.run()
    assert cfg.out_dir.stat().st_mode & 0o777 == 0o700
    assert list(cfg.out_dir.iterdir()) == []


def test_shared_or_symlink_recording_root_is_rejected(tmp_path):
    shared = tmp_path / "shared"
    shared.mkdir(mode=0o755)
    shared.chmod(0o755)
    bot = Fake(config(shared))
    with pytest.raises(BotError, match="must be private"):
        bot.run()
    assert bot.calls == []
    link = tmp_path / "linked"
    link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(BotError, match="must be private"):
        Fake(config(link)).run()
