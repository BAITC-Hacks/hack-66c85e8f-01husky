import socket

import pytest

from bots.urls import public_destination, validate_meeting_url


@pytest.mark.parametrize(
    ("platform", "url"),
    [
        ("meet", "https://meet.google.com/abc-defg-hij"),
        ("zoom", "https://us06web.zoom.us/j/12345678901?pwd=private"),
        ("zoom", "https://zoom.us/wc/123456789/join?pwd=private"),
        (
            "teams",
            "https://teams.microsoft.com/l/meetup-join/19%3ameeting_abc%40thread.v2/0?context=abc",
        ),
        ("teams", "https://teams.live.com/meet/123456789?p=private"),
        ("teams", "https://teams.microsoft.com/meet/123456789?p=private"),
    ],
)
def test_valid(platform, url):
    assert validate_meeting_url(platform, url) == url


@pytest.mark.parametrize(
    "url",
    [
        "http://meet.google.com/abc-defg-hij",
        "file:///abc-defg-hij",
        "https://meet.google.com:443/abc-defg-hij",
        "https://user@meet.google.com/abc-defg-hij",
        "https://meet.google.com/abc-defg-hij#secret",
        "https://meet.google.com.evil.org/abc-defg-hij",
        "https://127.0.0.1/abc-defg-hij",
        "https://meet.google.com/a",
        "https://meet.google.com/abc-defg-hij\n",
        "https://meet.google.com\\@evil.org/abc-defg-hij",
        "https://zoom.us/j/123456789",
        "https://localhost/abc-defg-hij",
    ],
)
def test_invalid(url):
    with pytest.raises(ValueError):
        validate_meeting_url("meet", url)


def test_dns_private_guard(monkeypatch):
    def lookup(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.2", 443))]

    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    assert not public_destination("https://public.example.com/api")
    assert not public_destination("https://127.0.0.1/api")
    assert not public_destination("http://public.example.com/api")
    assert not public_destination("https://public.example.com:8080/api")


def test_public_guard(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **kw: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))],
    )
    assert public_destination("https://assets.example.com/file.js")
    assert public_destination("wss://socket.example.com/ws")
