"""Real Chromium + local HTML fixtures. These do not prove live provider compatibility."""

import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from bots.base import BotConfig, BotError
from bots.browser import MUTE_CAPTURE
from bots.meet import MeetBot
from bots.teams import TeamsBot
from bots.zoom import ZoomBot


@pytest.fixture(scope="module")
def chromium():
    with sync_playwright() as playwright:
        channel = os.getenv("KENES_TEST_BROWSER_CHANNEL")
        if not channel and not Path(playwright.chromium.executable_path).exists():
            pytest.skip("Install Chromium: uv run playwright install chromium")
        browser = playwright.chromium.launch(chromium_sandbox=True, channel=channel)
        yield browser
        browser.close()


@pytest.mark.parametrize(
    ("cls", "platform", "field", "join", "leave"),
    [
        (MeetBot, "meet", '<input placeholder="Your name">', "Ask to join", "Leave call"),
        (ZoomBot, "zoom", '<input id="input-for-name">', "Join", "Leave"),
        (TeamsBot, "teams", '<input data-tid="prejoin-display-name-input">', "Join now", "Hang up"),
    ],
)
def test_prejoin_lobby_admission_and_end(chromium, tmp_path, cls, platform, field, join, leave):
    context = chromium.new_context()
    page = context.new_page()
    # HTML state transitions are driven by exactly the controls used by production adapters.
    page.set_content(f"""<body>{field}<button aria-label="Turn off microphone"
        onclick="this.setAttribute('aria-label','Turn on microphone')">mic</button>
        <button aria-label="Turn off camera"
        onclick="this.setAttribute('aria-label','Turn on camera')">cam</button>
        <button onclick="document.body.innerHTML='<p>Waiting for host</p>';setTimeout(() =>
        document.body.innerHTML='<button>{leave}</button>', 50)">{join}</button></body>""")
    bot = cls(BotConfig(platform, "private", 1, "private", "secret", out_dir=tmp_path))
    bot.page = page
    bot.context = context
    bot.open_browser = lambda url=None: None
    bot.join()
    page.wait_for_timeout(70)
    page.evaluate("""() => {
      const captions = document.createElement("button");
      captions.setAttribute("aria-label", "Turn on captions");
      const more = document.createElement("button");
      more.id = "callingButtons-showMoreBtn";
      const participants = document.createElement("button");
      participants.textContent = "Participants";
      document.body.append(captions, more, participants);
    }""")
    bot.wait_admitted(timeout_sec=3)
    assert bot.admitted
    page.set_content("<p>The meeting has ended</p>")
    assert bot.call_ended()
    bot.leave()
    assert page.is_closed()


@pytest.mark.parametrize(
    ("html", "reason"),
    [
        ("<p>The host denied your request</p>", "denied guest access"),
        ("<p>You can't join this video call</p>", "provider refused access"),
        (
            "<p>Zoom needs to review the security of your connection before proceeding.</p>",
            "CAPTCHA",
        ),
        ("<p>Sign in to join</p>", "requires sign-in"),
        ("<p>Verify you are human</p>", "CAPTCHA"),
    ],
)
def test_explicit_access_failures(chromium, html, reason):
    page = chromium.new_page()
    page.set_content(html)
    bot = MeetBot(BotConfig("meet", "private", 1, "private", "secret"))
    bot.page = page
    with pytest.raises(BotError, match=reason):
        bot.wait_admitted(1)
    page.close()


def test_lobby_timeout(chromium):
    page = chromium.new_page()
    page.set_content("<p>Waiting for the host to let you in</p>")
    bot = MeetBot(BotConfig("meet", "private", 1, "private", "secret"))
    bot.page = page
    with pytest.raises(BotError, match="lobby timeout"):
        bot.wait_admitted(0.01)
    page.close()


def test_capture_script_keeps_video_enabled(chromium):
    page = chromium.new_page()
    page.set_content('<canvas id="canvas"></canvas>')
    page.evaluate(MUTE_CAPTURE)
    result = page.evaluate("""() => {
        const source = document.querySelector('canvas').captureStream().getVideoTracks()[0];
        const clone = source.clone();
        clone.enabled = true;
        return clone.enabled;
    }""")
    assert result is True
    page.close()


@pytest.mark.parametrize(
    ("cls", "platform", "text", "leave", "control"),
    [
        (
            MeetBot,
            "meet",
            "Asking to be let in",
            "Leave call",
            '<button aria-label="Turn on captions"></button>',
        ),
        (
            TeamsBot,
            "teams",
            "Someone will let you in soon",
            "Leave",
            '<button id="callingButtons-showMoreBtn"></button>',
        ),
        (
            ZoomBot,
            "zoom",
            "Please wait, the meeting host will let you in soon",
            "Leave",
            "<button>Participants</button>",
        ),
    ],
)
def test_lobby_leave_button_does_not_mean_admitted(chromium, cls, platform, text, leave, control):
    page = chromium.new_page()
    bot = cls(BotConfig(platform, "private", 1, "private", "secret"))
    bot.page = page
    page.set_content(f"<p>{text}</p><button>{leave}</button>{control}")
    assert not bot.in_call()
    with pytest.raises(BotError, match="lobby timeout"):
        bot.wait_admitted(0.01)
    assert not bot.admitted
    page.set_content(f"<button>{leave}</button>")
    assert not bot.in_call()
    page.set_content(f"<button>{leave}</button>{control}")
    assert bot.in_call()
    page.close()


@pytest.mark.parametrize(
    "label", ["Ask to join anyway", "Join the call now", "Join anyway", "Join here too"]
)
def test_meet_join_label_and_blur_commits_exact_name(chromium, label):
    page = chromium.new_page()
    page.set_content(f"""<input aria-label="Your name" onblur="document.querySelector('button').disabled=false">
        <button disabled onclick="window.joinedName=document.querySelector('input').value">{label}</button>""")
    bot = MeetBot(BotConfig("meet", "private", 1, "private", "secret"))
    bot.page = page
    bot.open_browser = lambda url=None: None
    bot.join()
    assert page.evaluate("window.joinedName") == "Kenes AI"
    page.close()


@pytest.mark.parametrize("word", ["recorded", "captured"])
def test_meet_recording_notice_is_confirmed_before_admission(chromium, word):
    page = chromium.new_page()
    page.set_content(f"""<button>Leave call</button><button aria-label="Turn on captions"></button>
        <div role="alertdialog"><p>This meeting is being {word}</p>
        <button onclick="this.parentNode.remove()">Join</button></div>""")
    bot = MeetBot(BotConfig("meet", "private", 1, "private", "secret"))
    bot.page = page
    assert not bot.in_call()
    bot.wait_admitted(1)
    assert bot.admitted
    assert page.locator('[role="alertdialog"]').count() == 0
    page.close()


def test_teams_checked_controls_and_stable_join_selector(chromium):
    page = chromium.new_page()
    page.set_content("""<input data-tid="prejoin-display-name-input">
        <div data-tid="toggle-mute" checked="true" onclick="this.setAttribute('checked','false')">Mic</div>
        <div data-tid="toggle-video" checked="false" onclick="this.setAttribute('checked','true')">Camera</div>
        <button data-tid="prejoin-join-button" onclick="window.joinedName=document.querySelector('input').value">Join</button>""")
    bot = TeamsBot(BotConfig("teams", "private", 1, "private", "secret"))
    bot.page = page
    bot.open_browser = lambda url=None: None
    bot.join()
    assert page.evaluate("window.joinedName") == "Kenes AI"
    assert page.locator('[data-tid="toggle-mute"]').get_attribute("checked") == "false"
    assert page.locator('[data-tid="toggle-video"]').get_attribute("checked") == "true"
    page.close()


@pytest.mark.parametrize(
    ("html", "reason"),
    [
        ("<p>You were denied access to the meeting</p>", "denied guest access"),
        ("<p>Your request to join was declined</p>", "denied guest access"),
        ("<p>Verify you're a real person</p>", "CAPTCHA"),
        ("<p>We need to verify your info before you can join</p>", "requires sign-in"),
        ("<p>We couldn't connect you</p>", "could not connect"),
        ('<input name="loginfmt" type="email">', "requires sign-in"),
    ],
)
def test_teams_observed_access_states(chromium, html, reason):
    page = chromium.new_page()
    page.set_content(html)
    bot = TeamsBot(BotConfig("teams", "private", 1, "private", "secret"))
    bot.page = page
    with pytest.raises(BotError, match=reason):
        bot.assert_access()
    page.close()


@pytest.mark.parametrize(
    ("url", "top_level", "public", "allowed", "blocked_flag"),
    [
        ("https://www.google.com/frame", False, True, True, False),
        ("https://www.google.com/frame", True, True, False, True),
        ("https://private.example/frame", False, False, False, False),
        ("https://private.example/frame", True, False, False, True),
        ("https://us06web.zoom.us/wc/123456789/join", True, True, True, False),
    ],
)
def test_navigation_guard_distinguishes_provider_page_from_subframes(
    monkeypatch, url, top_level, public, allowed, blocked_flag
):
    from types import SimpleNamespace

    main_frame = object()
    bot = ZoomBot(BotConfig("zoom", "private", 1, "private", "secret"))
    bot.page = SimpleNamespace(main_frame=main_frame)
    request = SimpleNamespace(
        url=url, frame=main_frame if top_level else object(), is_navigation_request=lambda: True
    )
    result = []
    route = SimpleNamespace(
        request=request,
        continue_=lambda: result.append("allowed"),
        abort=lambda reason: result.append("blocked"),
    )
    monkeypatch.setattr("bots.browser.public_destination", lambda url: public)
    bot._route(route)
    assert result == ["allowed" if allowed else "blocked"]
    assert bot.blocked_navigation is blocked_flag


def test_meet_media_permission_prompt_after_join(chromium):
    page = chromium.new_page()
    page.set_content("""<body>
      <p>Do you want people to see and hear you in the meeting?</p>
      <button>Continue without microphone and camera</button>
    </body>""")
    page.get_by_role("button").evaluate("""button => button.onclick = () => {
      document.body.innerHTML = '<button>Leave call</button>' +
        '<button aria-label="Turn on captions">Captions</button>';
    }""")
    bot = MeetBot(BotConfig("meet", "private", 1, "private", "secret"))
    bot.page = page
    try:
        bot.wait_admitted(1)
        assert bot.admitted
    finally:
        page.close()
