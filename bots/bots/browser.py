"""Bounded guest browser state machine shared by the three web clients."""

from __future__ import annotations

import re
import time
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

from bots.base import BotError, MeetingBot, child_environment
from bots.media import CAMERA_HEIGHT, CAMERA_WIDTH, prepare_media
from bots.urls import public_destination, validate_meeting_url

# UI mute is defense in depth. Native fake microphone input contains only zeros.
# Video stays enabled so the static project logo reaches the call.
MUTE_CAPTURE = """(() => {
  const mute = track => {
    if (track.kind !== "audio") { track.contentHint = "detail"; return track; }
    track.enabled = false;
    Object.defineProperty(track, 'enabled', {get: () => false, set: () => {}});
    return track;
  };
  const clone = MediaStreamTrack.prototype.clone;
  MediaStreamTrack.prototype.clone = function() { return mute(clone.call(this)); };
  const devices = navigator.mediaDevices;
  if (devices) {
    const acquire = devices.getUserMedia.bind(devices);
    devices.getUserMedia = async constraints => {
      const stream = await acquire(constraints);
      stream.getTracks().forEach(mute);
      const preferred = (value, size) => {
        if (value && typeof value === 'object') {
          if ('exact' in value) return value;
          return {...value, ideal: size};
        }
        return {ideal: size};
      };
      for (const track of stream.getVideoTracks()) {
        const current = track.getConstraints();
        try {
          await track.applyConstraints({...current,
            width: preferred(current.width, __CAMERA_WIDTH__),
            height: preferred(current.height, __CAMERA_HEIGHT__)});
        } catch (error) {
          // Keep the valid capture if provider requirements cannot fit our preferred size.
          if (error.name !== 'OverconstrainedError') throw error;
        }
      }
      return stream;
    };
  }
})();""".replace("__CAMERA_WIDTH__", str(CAMERA_WIDTH)).replace(
    "__CAMERA_HEIGHT__", str(CAMERA_HEIGHT)
)


class BrowserBot(MeetingBot):
    name_selectors: tuple[str, ...] = ()
    join_labels: tuple[str, ...] = ()
    join_selectors: tuple[str, ...] = ()
    leave_labels: tuple[str, ...] = ()
    leave_selectors: tuple[str, ...] = ()
    in_call_selectors: tuple[str, ...] = ()
    in_call_labels: tuple[str, ...] = ()
    lobby_pattern = re.compile(
        r"asking to be let in|waiting for (?:the )?host|waiting (?:for someone )?to be admitted|"
        r"someone (?:in the meeting )?(?:will|should) let you in|host will let you in|"
        r"(?:know|see) you.re waiting|waiting for someone to let you in|"
        r"host to start (?:this |the )?meeting|ожидайте.*(?:организатор|допуск)",
        re.IGNORECASE,
    )
    mute_labels = (
        r"^Turn off microphone",
        r"^Mute(?: my)? (?:microphone|audio)$",
        r"^Mute$",
        r"^Выключить микрофон",
        r"^Отключить микрофон",
    )
    camera_labels = (
        r"^Turn on camera",
        r"^Start (?:my )?video$",
        r"^Включить камеру",
        r"^Начать видео",
    )
    ended_pattern = re.compile(
        r"(?:you (?:have )?(?:left|were removed from) (?:the )?(?:meeting|call)|"
        r"meeting (?:has )?ended|call (?:has )?ended|you.ve been removed|"
        r"встреча завершена|собрание завершено|вы покинули|вас удалили)",
        re.IGNORECASE,
    )
    denied_pattern = re.compile(
        r"(?:request to join (?:was )?(?:denied|declined)|can.t join this (?:video call|call|meeting)|"
        r"not (?:allowed|permitted) to join|declined your request|"
        r"denied your request|denied access to the meeting|meeting (?:is )?locked|"
        r"запрос отклонен|запрос отклонён|не разрешил|не можете присоединиться)",
        re.IGNORECASE,
    )
    auth_pattern = re.compile(
        r"(?:sign in to join|sign in to this meeting|only authenticated users|"
        r"requires? authentication|log in to join|need to be signed in|need to sign in|"
        r"sign in to Teams to join|to join this meeting, sign in again|"
        r"we need to verify your info before you can join|войдите.*(?:присоединиться|собранию))",
        re.IGNORECASE,
    )

    def __init__(self, cfg):
        super().__init__(cfg)
        self.playwright = self.context = self.page = None
        self.admitted = False
        self.blocked_navigation = False

    def open_browser(self, url: str | None = None) -> None:
        url = validate_meeting_url(self.cfg.platform, url or self.cfg.url)
        camera, microphone = prepare_media(self.work_dir)
        self.playwright = sync_playwright().start()
        self.context = self.playwright.chromium.launch_persistent_context(
            str(self.work_dir / "browser"),
            headless=self.cfg.headless,
            chromium_sandbox=True,
            env=child_environment(),
            locale="en-US",
            accept_downloads=False,
            service_workers="block",
            permissions=["microphone", "camera"],
            args=[
                "--autoplay-policy=no-user-gesture-required",
                # Live Meet rejected ResolveMeetingSpace before the name form in
                # Chrome's automation mode. This only restores prejoin access;
                # meeting admission still depends on the provider and host.
                *(
                    ["--disable-blink-features=AutomationControlled"]
                    if self.cfg.platform == "meet"
                    else []
                ),
                "--use-fake-device-for-media-stream",
                f"--use-file-for-fake-video-capture={camera}",
                f"--use-file-for-fake-audio-capture={microphone}",
            ],
            ignore_default_args=["--mute-audio"],
        )
        self.context.set_default_timeout(5000)
        self.context.add_init_script(MUTE_CAPTURE)
        self.context.route("**/*", self._route)
        self.context.route_web_socket("**/*", self._websocket)
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.goto(url, wait_until="domcontentloaded", timeout=45000)

    def _route(self, route) -> None:
        request = route.request
        permitted = public_destination(request.url)
        if (
            request.is_navigation_request()
            and self.page is not None
            and request.frame == self.page.main_frame
        ):
            host = (urlsplit(request.url).hostname or "").lower()
            roots = {
                "meet": ("google.com",),
                "zoom": ("zoom.us",),
                "teams": ("microsoft.com", "live.com", "microsoftonline.com", "cloud.microsoft"),
            }
            permitted = permitted and any(
                host == root or host.endswith("." + root) for root in roots[self.cfg.platform]
            )
            if not permitted:
                self.blocked_navigation = True
        if permitted:
            route.continue_()
        else:
            route.abort("blockedbyclient")

    @staticmethod
    def _websocket(route) -> None:
        if public_destination(route.url):
            route.connect_to_server()
        else:
            route.close()

    def visible(self, selectors):
        for selector in selectors:
            elements = self.page.locator(selector)
            for index in range(min(elements.count(), 10)):
                element = elements.nth(index)
                if element.is_visible():
                    return element
        return None

    def button(self, patterns):
        for pattern in patterns:
            elements = self.page.get_by_role("button", name=re.compile(pattern, re.IGNORECASE))
            for index in range(min(elements.count(), 10)):
                element = elements.nth(index)
                if element.is_visible() and element.is_enabled():
                    return element
        return None

    def click_optional(self, patterns) -> bool:
        button = self.button(patterns)
        if button is not None:
            button.click()
            return True
        return False

    def assert_access(self) -> None:
        if self.blocked_navigation:
            raise BotError("Browser blocked an unsafe meeting redirect")
        if self.page.is_closed():
            raise BotError("Meeting browser closed unexpectedly")
        host = (urlsplit(self.page.url).hostname or "").lower()
        if host in {"accounts.google.com", "login.microsoftonline.com", "login.live.com"}:
            raise BotError("Meeting requires sign-in; guest access is unavailable")
        if (
            self.visible(
                (
                    'iframe[src*="recaptcha"][title*="challenge"]',
                    'iframe[src*="hcaptcha"]',
                    'input[name="captcha"]',
                )
            )
            is not None
        ):
            raise BotError("Meeting requires CAPTCHA; manual participation is required")
        # Read locally for matching only. Never persist screenshots, text, URLs or cookies.
        body = self.page.locator("body").inner_text(timeout=5000)
        if re.search(r"can.t join this (?:video call|call|meeting)", body, re.IGNORECASE):
            raise BotError("Meeting provider refused access; the reason was not disclosed")
        if self.denied_pattern.search(body):
            raise BotError("Organizer denied guest access or locked the meeting")
        if self.auth_pattern.search(body):
            raise BotError("Meeting requires sign-in; guest access is unavailable")
        if re.search(
            r"(?:verify (?:that )?you are human|verify you.re not a robot|verify you.re a real person|"
            r"review the security of your connection|performing security verification)",
            body,
            re.IGNORECASE,
        ):
            raise BotError("Meeting requires CAPTCHA; manual participation is required")

    def prejoin_step(self) -> None:
        """Optional provider landing-page controls, with bounded invocation."""

    def admission_step(self) -> None:
        """Provider confirmation dialogs that can appear after the join request."""

    def mute(self) -> None:
        self.click_optional(self.mute_labels)
        self.click_optional(self.camera_labels)

    def join(self) -> None:
        self.open_browser()
        deadline = time.monotonic() + 90
        name_filled = False
        while time.monotonic() < deadline:
            self.assert_access()
            self.prejoin_step()
            field = self.visible(self.name_selectors)
            if field is not None and field.is_editable():
                if field.input_value() != self.cfg.display_name:
                    field.fill(self.cfg.display_name)
                    field.press("Tab")
                name_filled = field.input_value() == self.cfg.display_name
            self.mute()
            join = self.visible(self.join_selectors)
            if join is None:
                join = self.button(self.join_labels)
            if name_filled and join is not None and join.is_enabled():
                join.click()
                return
            self.page.wait_for_timeout(500)
        raise BotError("Guest prejoin controls were not found; provider UI may have changed")

    def in_call(self) -> bool:
        if self.lobby_pattern.search(self.page.locator("body").inner_text()):
            return False
        has_leave = (
            self.button(self.leave_labels) is not None
            or self.visible(self.leave_selectors) is not None
        )
        has_call_controls = (
            self.visible(self.in_call_selectors) is not None
            or self.button(self.in_call_labels) is not None
        )
        return has_leave and has_call_controls

    def after_admission(self) -> None:
        self.mute()

    def wait_admitted(self, timeout_sec: int = 600) -> None:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            self.assert_access()
            self.admission_step()
            if self.in_call():
                self.admitted = True
                self.after_admission()
                return
            if self.ended_pattern.search(self.page.locator("body").inner_text()):
                raise BotError("Meeting ended before admission")
            self.page.wait_for_timeout(500)
        raise BotError("Organizer did not admit the bot before the lobby timeout")

    def call_ended(self) -> bool:
        self.assert_access()
        self.mute()
        return bool(self.ended_pattern.search(self.page.locator("body").inner_text()))

    def leave(self) -> None:
        try:
            if (
                self.page is not None
                and not self.page.is_closed()
                and not self.click_optional(self.leave_labels)
            ):
                leave = self.visible(self.leave_selectors)
                if leave is not None:
                    leave.click()
        finally:
            try:
                if self.context is not None:
                    self.context.close()
            finally:
                self.context = self.page = None
                if self.playwright is not None:
                    self.playwright.stop()
                    self.playwright = None
