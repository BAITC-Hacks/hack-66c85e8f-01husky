"""Render the checked-in develop logo as the bot camera frame."""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

assets = Path(__file__).resolve().parents[1] / "bots" / "assets"
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        headless=True, channel=os.getenv("KENES_TEST_BROWSER_CHANNEL")
    )
    try:
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page.set_content(
            "<html><style>html,body{margin:0;width:100%;height:100%;background:#F7F6FC}"
            "body{display:flex;align-items:center;justify-content:center}"
            "svg{width:1440px;height:auto}</style><body>"
            + (assets / "kenes-ai-light.svg").read_text()
            + "</body></html>"
        )
        page.screenshot(path=str(assets / "camera.png"))
    finally:
        browser.close()
