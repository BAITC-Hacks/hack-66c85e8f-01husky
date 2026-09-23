# Camera asset

`kenes-ai-light.svg` is an unchanged copy of `frontend/public/brand/kenes-ai-light.svg` from upstream develop commit `e8f97e71f813ae976c15523d4bbbc18cba2ff01a`. The user requested the existing project logo for the bot.

`camera.png` renders that SVG at 1440 px width, centered in a 1920×1080 frame, with background `#F7F6FC`. Runtime converts this static frame to a one-frame looping Y4M source for Chromium. No camera hardware is used.

Regenerate with `uv run python scripts/render_camera.py` from `bots/`. Requires installed Playwright Chromium; set `KENES_TEST_BROWSER_CHANNEL=chrome` to use system Google Chrome.
