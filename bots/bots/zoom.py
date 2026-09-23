"""Zoom web client (zoom.us/wc/<id>/join). Owner: Ардак. Selectors are the only platform-specific part."""

from bots.base import MeetingBot


class ZoomBot(MeetingBot):
    def join(self) -> None:
        raise NotImplementedError(
            "zoom adapter: open URL via Playwright, set name, mute, click join"
        )

    def wait_admitted(self, timeout_sec: int = 600) -> None:
        raise NotImplementedError("zoom adapter: wait for in-call UI")

    def call_ended(self) -> bool:
        raise NotImplementedError("zoom adapter: detect 'call ended' / removed state")

    def leave(self) -> None:
        raise NotImplementedError("zoom adapter: click leave, close browser")
