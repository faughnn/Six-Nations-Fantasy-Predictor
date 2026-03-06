"""
Explore API endpoints to find league-specific member lists.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.scrapers.fantasy_sixnations import DEFAULT_SESSION_PATH

BASE_URL = "https://fantasy.sixnationsrugby.com"


async def api_fetch(page, endpoint):
    return await page.evaluate(
        """async (endpoint) => {
            const token = localStorage.getItem('jwtToken600') || '';
            const resp = await fetch(endpoint, {
                headers: {
                    'Authorization': 'Token ' + token,
                    'x-access-key': '600@18.23@',
                    'Accept': 'application/json',
                }
            });
            if (!resp.ok) return {_error: resp.status, _url: endpoint};
            return await resp.json();
        }""",
        endpoint,
    )


async def main():
    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    )
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        no_viewport=True,
        storage_state=str(DEFAULT_SESSION_PATH),
    )
    page = await context.new_page()

    # Capture API responses when navigating
    api_responses = {}
    async def on_resp(response):
        if "/v1/" in response.url:
            try:
                body = await response.text()
                api_responses[response.url] = body
            except:
                pass
    page.on("response", on_resp)

    try:
        print("Loading site...")
        await page.goto(f"{BASE_URL}/m6n/#/game/play/me", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4)
        for sel in ['button:has-text("Accept")', 'button:has-text("Accept All")', '#onetrust-accept-btn-handler']:
            try:
                elem = await page.query_selector(sel)
                if elem and await elem.is_visible():
                    await elem.click()
                    await asyncio.sleep(1)
            except:
                pass
        await asyncio.sleep(2)

        # Test 1: Try different endpoint patterns for league-specific rankings
        # Reggie Classic = 122521 (should be a tiny league)
        test_league = 122521
        print(f"\n--- Testing endpoints for Reggie Classic (id={test_league}) ---")

        endpoints = [
            f"/v1/private/classementgroupe/{test_league}?lg=en",
            f"/v1/private/classement/{test_league}?lg=en",
            f"/v1/private/groupe/{test_league}/classement?lg=en",
            f"/v1/private/classementgeneral/{test_league}?lg=en",
            f"/v1/private/infosgroupe/{test_league}?lg=en",
            f"/v1/private/groupe/{test_league}?lg=en",
            f"/v1/private/membresgroupe/{test_league}?lg=en",
            f"/v1/private/membres/{test_league}?lg=en",
            f"/v1/private/groupe/{test_league}/membres?lg=en",
        ]

        for ep in endpoints:
            data = await api_fetch(page, ep)
            if isinstance(data, dict) and "_error" in data:
                print(f"  {ep} -> {data['_error']}")
            else:
                preview = json.dumps(data, ensure_ascii=False)[:300]
                print(f"  {ep} -> {preview}")
            await asyncio.sleep(0.2)

        # Test 2: Navigate to RANKINGS page and click on a private league
        # to intercept the actual API call the frontend makes
        print("\n--- Intercepting API calls from rankings page ---")
        api_responses.clear()
        await page.goto(f"{BASE_URL}/m6n/#/game/rankings", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)

        print(f"  API calls from initial rankings load:")
        for url in api_responses:
            if '/v1/' in url:
                print(f"    {url}")

        # Now click on "Reggie Classic" league
        api_responses.clear()
        reggie = await page.query_selector('text="Reggie Classic"')
        if reggie:
            print("  Clicking 'Reggie Classic'...")
            await reggie.click()
            await asyncio.sleep(4)

            print(f"  API calls after clicking Reggie Classic:")
            for url, body in api_responses.items():
                if '/v1/' in url:
                    print(f"    {url}")
                    try:
                        d = json.loads(body)
                        if isinstance(d, dict):
                            for k, v in d.items():
                                if isinstance(v, list):
                                    print(f"      {k}: list of {len(v)}")
                                    if v and isinstance(v[0], dict):
                                        print(f"        First: {json.dumps(v[0], ensure_ascii=False)[:200]}")
                                elif isinstance(v, (int, float, str, bool)):
                                    print(f"      {k}: {v}")
                    except:
                        print(f"      Raw: {body[:200]}")
        else:
            print("  Could not find 'Reggie Classic' element")

        # Test 3: Also try Nianna
        api_responses.clear()
        nianna = await page.query_selector('text="Nianna"')
        if nianna:
            print("\n  Clicking 'Nianna'...")
            await nianna.click()
            await asyncio.sleep(4)

            print(f"  API calls after clicking Nianna:")
            for url, body in api_responses.items():
                if '/v1/' in url:
                    print(f"    {url}")
                    try:
                        d = json.loads(body)
                        if isinstance(d, dict):
                            for k, v in d.items():
                                if isinstance(v, list):
                                    print(f"      {k}: list of {len(v)}")
                                    if v and isinstance(v[0], dict):
                                        print(f"        First: {json.dumps(v[0], ensure_ascii=False)[:200]}")
                                elif isinstance(v, (int, float, str, bool)):
                                    print(f"      {k}: {v}")
                    except:
                        print(f"      Raw: {body[:200]}")

        # Test 4: Check the "IRELAND FANS LEAGUE" which should have many members
        api_responses.clear()
        ireland = await page.query_selector('text="IRELAND FANS LEAGUE"')
        if ireland:
            print("\n  Clicking 'IRELAND FANS LEAGUE'...")
            await ireland.click()
            await asyncio.sleep(4)

            print(f"  API calls after clicking IRELAND FANS LEAGUE:")
            for url, body in api_responses.items():
                if '/v1/' in url:
                    print(f"    {url}")
                    try:
                        d = json.loads(body)
                        if isinstance(d, dict):
                            for k, v in d.items():
                                if isinstance(v, list):
                                    print(f"      {k}: list of {len(v)}")
                                elif isinstance(v, (int, float, str, bool)):
                                    print(f"      {k}: {v}")
                    except:
                        pass

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await context.storage_state(path=str(DEFAULT_SESSION_PATH))
        await browser.close()
        await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
