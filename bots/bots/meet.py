"""Google Meet web client (meet.google.com). Owner: Ардак. Selectors are the only platform-specific part."""

from bots.base import MeetingBot


class MeetBot(MeetingBot):
    def join(self) -> None:
        raise NotImplementedError(
            "meet adapter: open URL via Playwright, set name, mute, click join"
        )

    def wait_admitted(self, timeout_sec: int = 600) -> None:
        raise NotImplementedError("meet adapter: wait for in-call UI")

    def call_ended(self) -> bool:
        raise NotImplementedError("meet adapter: detect 'call ended' / removed state")

    def leave(self) -> None:
        raise NotImplementedError("meet adapter: click leave, close browser")
