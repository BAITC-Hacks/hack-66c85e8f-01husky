"""Microsoft Teams web client (teams.microsoft.com, 'Continue on this browser'). Owner: Ардак. Selectors are the only platform-specific part."""

from bots.base import MeetingBot


class TeamsBot(MeetingBot):
    def join(self) -> None:
        raise NotImplementedError(
            "teams adapter: open URL via Playwright, set name, mute, click join"
        )

    def wait_admitted(self, timeout_sec: int = 600) -> None:
        raise NotImplementedError("teams adapter: wait for in-call UI")

    def call_ended(self) -> bool:
        raise NotImplementedError("teams adapter: detect 'call ended' / removed state")

    def leave(self) -> None:
        raise NotImplementedError("teams adapter: click leave, close browser")
