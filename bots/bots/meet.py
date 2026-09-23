"""Google Meet guest prejoin and in-call controls (English locale)."""

import re

from bots.browser import BrowserBot


class MeetBot(BrowserBot):
    name_selectors = (
        'input[placeholder="Your name"]',
        'input[aria-label="Your name"]',
        'input[placeholder="Ваше имя"]',
        'input[aria-label="Ваше имя"]',
    )
    join_labels = (
        r"^Ask to join(?: anyway)?$",
        r"^Join the call now$",
        r"^Join anyway$",
        r"^Join here too$",
        r"^Join now$",
        r"^Попросить присоединиться$",
        r"^Присоединиться$",
    )
    leave_labels = (r"^Leave call", r"^Leave meeting", r"^Покинуть звонок", r"^Покинуть встречу")
    in_call_selectors = (
        'button[aria-label="Turn on captions"]',
        'button[aria-label="Turn off captions"]',
    )

    def prejoin_step(self) -> None:
        self.click_optional((r"^Continue without microphone and camera$", r"^Got it$"))

    def mute(self) -> None:
        super().mute()
        # Some Meet releases render labelled div controls without role=button.
        for selector in (
            'div[aria-label="Turn off microphone"]',
            'div[aria-label="Turn on camera"]',
        ):
            control = self.visible((selector,))
            if control is not None:
                control.click()

    def recording_dialog(self):
        dialogs = self.page.locator('[role="alertdialog"], [role="dialog"]')
        for index in range(min(dialogs.count(), 5)):
            dialog = dialogs.nth(index)
            if dialog.is_visible() and re.search(
                r"being (?:recorded|captured)", dialog.inner_text(), re.IGNORECASE
            ):
                return dialog
        return None

    def admission_step(self) -> None:
        self.prejoin_step()  # Media permission confirmation can appear after Join.
        dialog = self.recording_dialog()
        if dialog is not None:
            buttons = dialog.get_by_role(
                "button", name=re.compile(r"^Join(?: now)?$", re.IGNORECASE)
            )
            for index in range(min(buttons.count(), 5)):
                button = buttons.nth(index)
                if button.is_visible() and button.is_enabled():
                    button.click()
                    return

    def in_call(self) -> bool:
        return self.recording_dialog() is None and super().in_call()
