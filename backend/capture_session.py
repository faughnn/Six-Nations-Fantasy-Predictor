"""
Standalone script to capture and save a Fantasy Six Nations login session.

Opens a browser, lets you log in, then saves the session (cookies + localStorage)
so that future scraper runs can use it without manual login.

Usage:
    python capture_session.py
    python capture_session.py --clear   # Force fresh login
"""

import asyncio
import argparse
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright

from app.scrapers.fantasy_sixnations import DEFAULT_SESSION_PATH, BASE_URL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

GAME_URL = f"{BASE_URL}/m6n/#/game/play/me"
TIMEOUT = 300  # 5 minutes to log in


async def main():
    parser = argparse.ArgumentParser(description="Capture Fantasy Six Nations session token")
    parser.add_argument("--clear", action="store_true", help="Delete existing session first")
    args = parser.parse_args()

    session_path = DEFAULT_SESSION_PATH

    if args.clear and session_path.exists():
        session_path.unlink()
        print("Cleared existing session.")

    print("=" * 60)
    print("FANTASY SIX NATIONS — SESSION CAPTURE")
    print("=" * 60)
    print()
    print("A browser will open. Please log in to your account.")
    print("The session will be saved automatically once login is detected.")
    print()

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    )
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        no_viewport=True,
    )
    page = await context.new_page()

    await page.goto(GAME_URL, wait_until="domcontentloaded", timeout=60000)

    # Dismiss cookie banners
    await asyncio.sleep(2)
    for sel in ['button:has-text("Accept")', 'button:has-text("Accept All")', '#onetrust-accept-btn-handler']:
        try:
            elem = await page.query_selector(sel)
            if elem and await elem.is_visible():
                await elem.click()
                print(f"Dismissed overlay: {sel}")
                await asyncio.sleep(1)
                break
        except Exception:
            continue

    print("Waiting for login...")

    # Wait for the auth token (600cv) to appear in localStorage.
    # The app writes this AFTER the login flow completes, which can be
    # well after UI elements like app-game render.
    for i in range(TIMEOUT):
        await asyncio.sleep(1)

        try:
            token = await page.evaluate("() => localStorage.getItem('600cv')")
            if token and len(token) > 10:
                print(f"Login detected! (600cv token present, {len(token)} chars)")
                # Give it a moment to settle and write any remaining state
                await asyncio.sleep(3)
                break

            # Progress indicator
            if i > 0 and i % 15 == 0:
                print(f"Still waiting for login... ({i}s elapsed)")

        except Exception:
            # Page navigating (OAuth redirect etc.) — keep waiting
            if i > 0 and i % 15 == 0:
                print(f"Still waiting for login... ({i}s elapsed)")
            continue
    else:
        print(f"\nTimed out after {TIMEOUT}s. No session saved.")
        await browser.close()
        await pw.stop()
        return

    # Save session
    session_path.parent.mkdir(parents=True, exist_ok=True)
    await context.storage_state(path=str(session_path))
    print(f"\nSession saved to {session_path}")
    print("You can now run scrapers — they will use this session automatically.")

    await browser.close()
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
