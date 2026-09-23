"""Zoom browser guest client. Invitation passwords remain in the private URL."""

import re
from urllib.parse import parse_qs, urlsplit, urlunsplit

from bots.base import BotError
from bots.browser import BrowserBot
from bots.urls import validate_meeting_url


class ZoomBot(BrowserBot):
    name_selectors = (
        "#input-for-name",
        "#inputname",
        'input[placeholder="Your Name"]',
        'input[placeholder="Your name"]',
        'input[aria-label="Your Name"]',
    )
    join_labels = (r"^Join$", r"^Join Meeting$", r"^Присоединиться$", r"^Войти$")
    leave_labels = (r"^Leave$", r"^Leave Meeting$", r"^Выйти$", r"^Выйти из конференции$")
    in_call_labels = (r"^Participants(?:\b.*)?$",)

    def open_browser(self, url=None) -> None:
        parts = urlsplit(validate_meeting_url(self.cfg.platform, url or self.cfg.url))
        path = re.sub(r"^/j/(\d+)$", r"/wc/\1/join", parts.path)
        super().open_browser(urlunsplit((parts.scheme, parts.netloc, path, parts.query, "")))

    def prejoin_step(self) -> None:
        self.click_optional((r"^Accept Cookies$", r"^I Agree$", r"^Join from Your Browser$"))
        password = self.visible(("#input-for-pwd", 'input[type="password"]'))
        if password is not None:
            # Zoom pwd is commonly encrypted and must be consumed by its URL handler.
            # Never fill an encrypted invitation token as a plaintext passcode.
            if not parse_qs(urlsplit(self.cfg.url).query).get("pwd"):
                raise BotError("Zoom requires a passcode; use the complete invitation link")
            raise BotError("Zoom did not accept the invitation passcode")

    def mute(self) -> None:
        # The audio dialog can arrive after the in-call toolbar. Retry during recording.
        if self.admitted:
            self.click_optional((r"^Join Audio$", r"^Join audio by computer$"))
            self.click_optional((r"^Join Audio by Computer$", r"^Join with Computer Audio$"))
        super().mute()

    def leave(self) -> None:
        try:
            if (
                self.page is not None
                and not self.page.is_closed()
                and self.click_optional(self.leave_labels)
            ):
                self.click_optional((r"^Leave Meeting$", r"^Leave$"))
        finally:
            super().leave()
