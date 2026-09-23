"""Provider URL validation shared by the API and the bot runner."""

import ipaddress
import re
import socket
from urllib.parse import urlsplit, urlunsplit


def validate_meeting_url(platform: str, url: str) -> str:
    """Return a normalized HTTPS invitation URL, without following it."""
    if any(ord(c) < 33 for c in url) or "\\" in url:
        raise ValueError("Meeting URL contains invalid characters")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise ValueError("Invalid meeting URL") from None
    host = (parts.hostname or "").lower()
    if (
        parts.scheme != "https"
        or parts.username is not None
        or parts.password is not None
        or port is not None
        or parts.fragment
    ):
        raise ValueError("Meeting URL must use HTTPS without credentials, port or fragment")
    valid = False
    if platform == "meet":
        valid = host == "meet.google.com" and bool(
            re.fullmatch(r"/[a-z]{3}-[a-z]{4}-[a-z]{3}/?", parts.path)
        )
    elif platform == "zoom":
        valid = (host == "zoom.us" or host.endswith(".zoom.us")) and bool(
            re.fullmatch(r"/(?:j/\d{9,11}|wc/\d{9,11}/join)/?", parts.path)
        )
    elif platform == "teams":
        valid = host in {"teams.microsoft.com", "teams.live.com"} and bool(
            re.fullmatch(r"/meet/\d+(?:/[^/]+)?/?", parts.path)
            or (
                host == "teams.microsoft.com"
                and re.fullmatch(r"/l/meetup-join/[^/]+/[^/]+/?", parts.path)
            )
        )
    if not valid:
        raise ValueError("URL does not match the selected meeting platform")
    return urlunsplit(("https", host, parts.path.rstrip("/"), parts.query, ""))


def public_destination(url: str) -> bool:
    """Reject local/IP destinations, including DNS resolving to private addresses.

    Browser routing is defense in depth, not a replacement for network egress rules.
    DNS rebinding and WebRTC traffic require isolation at the container/network layer.
    """
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
        if parts.scheme not in {"https", "wss"} or parts.port not in {None, 443}:
            return False
        if parts.username is not None or parts.password is not None or not host:
            return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            pass
        if "." not in host or host.endswith((".localhost", ".local", ".internal")):
            return False
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(a[4][0]).is_global for a in addresses)
    except (OSError, ValueError):
        return False
