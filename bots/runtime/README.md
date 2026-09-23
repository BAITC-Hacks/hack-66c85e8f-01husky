# Chromium sandbox in Docker

`seccomp_profile.json` is the unmodified profile from Microsoft Playwright v1.63.0:
https://github.com/microsoft/playwright/blob/v1.63.0/utils/docker/seccomp_profile.json

License: `PLAYWRIGHT_LICENSE` (Apache-2.0).

SHA256: `cc3e61cabda6bbc1e53e54d27ba4d55a9d3be829b6dd1a596f4a7b31b1cc7849`.

Playwright documents this Docker profile for a non-root Chromium process with its
sandbox enabled. It retains a default deny action and adds namespace creation
syscalls (`clone`, `setns`, `unshare`). It does not grant SYS_ADMIN or run the
container in privileged mode. Use only for the bot-worker service.

The default Docker profile reproduced a Chromium sandbox startup failure in the
local Colima runtime. This profile passed the real Chromium → PulseAudio → ffmpeg
440 Hz recording check. The profile does not control network egress or guarantee
admission to an external meeting.
