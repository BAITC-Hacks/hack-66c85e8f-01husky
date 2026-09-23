"""Teams business/personal browser guest entry, lobby and meeting controls."""

import re

from bots.base import BotError
from bots.browser import BrowserBot


class TeamsBot(BrowserBot):
    name_selectors = (
        'input[data-tid="prejoin-display-name-input"]',
        'input[placeholder="Type your name"]',
        'input[placeholder="Enter name"]',
        'input[aria-label="Name"]',
        'input[placeholder="Введите имя"]',
    )
    join_labels = (
        r"^Join now$",
        r"^Join meeting$",
        r"^Присоединиться сейчас$",
        r"^Присоединиться$",
    )
    join_selectors = ('[data-tid="prejoin-join-button"]',)
    leave_selectors = ('[data-inp="hangup-button"]', "#hangup-button")
    leave_labels = (r"^Leave(?: .*)?$", r"^Hang up$", r"^Покинуть.*$", r"^Завершить звонок$")
    in_call_selectors = ("#callingButtons-showMoreBtn",)

    def prejoin_step(self) -> None:
        self.click_optional(
            (
                r"^Continue on this browser$",
                r"^Join on the web instead$",
                r"^Continue without signing in$",
                r"^Join as a guest$",
                r"^Продолжить в этом браузере$",
            )
        )
        # Teams renders some landing choices as links rather than buttons.
        for selector in ('[data-tid="joinOnWeb"]', "#joinOnWeb"):
            link = self.visible((selector,))
            if link is not None:
                link.click()

    def mute(self) -> None:
        super().mute()
        for selector, toggle_from in (
            ('[data-tid="toggle-mute"]', "true"),
            ('[data-tid="toggle-video"]', "false"),
        ):
            switch = self.visible((selector,))
            if switch is not None:
                state = switch.get_attribute("aria-checked")
                if state is None:
                    state = switch.get_attribute("checked")
                if state == toggle_from:
                    switch.click()

    def assert_access(self) -> None:
        super().assert_access()
        if self.visible(('input[name="loginfmt"][type="email"]',)) is not None:
            raise BotError("Meeting requires sign-in; guest access is unavailable")
        body = self.page.locator("body").inner_text()
        if re.search(r"meeting URL is incorrect|we couldn.t connect you", body, re.IGNORECASE):
            raise BotError("Teams could not connect; check the invitation and meeting availability")
