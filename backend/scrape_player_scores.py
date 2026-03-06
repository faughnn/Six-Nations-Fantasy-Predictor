"""Dump full feuillematch for High Tackle round 1 to see all fields."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.scrapers.fantasy_sixnations import DEFAULT_SESSION_PATH

BASE_URL = "https://fantasy.sixnationsrugby.com"


async def api_fetch(page, endpoint):
    return await page.evaluate(
        "async (endpoint) => {"
        "  const token = localStorage.getItem('jwtToken600') || '';"
        "  const r = await fetch(endpoint, {credentials:'include', headers:{"
        "    'Authorization':'Token '+token,"
        "    'x-access-key':'600@18.23@',"
        "    'Accept':'application/json'"
        "  }});"
        "  if (!r.ok) return {_error: r.status};"
        "  return await r.json();"
        "}",
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

    print("Loading site...")
    await page.goto(f"{BASE_URL}/m6n/#/game/play/me", wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(4)

    # Get full feuillematch for High Tackle, all 3 rounds
    for rnd in range(1, 4):
        d = await api_fetch(page, f"/v1/private/feuillematch/{rnd}/29793?lg=en")
        if isinstance(d, dict) and "_error" not in d:
            with open(f"data/feuillematch_ht_r{rnd}.json", "w") as f:
                json.dump(d, f, indent=2, ensure_ascii=False)

            feuille = d.get("feuille", {})
            postes = feuille.get("postes", [])
            round_total = 0
            print(f"\nRound {rnd} - High Tackle's squad:")
            for p in postes:
                nom = p.get("nom", "empty")
                pts = p.get("points", p.get("pts", p.get("score", "?")))
                club = p.get("club", "")
                place = p.get("place", "")
                cap = p.get("est_capitaine", False)
                sub = p.get("est_supersub", False)
                # Check all numeric fields
                nums = {k: v for k, v in p.items() if isinstance(v, (int, float)) and v != 0}
                if nom != "empty" and p.get("occupe"):
                    role = ""
                    if cap:
                        role = " (C)"
                    if sub:
                        role = " (SS)"
                    print(f"  {nom:<25} {club:<10} pts={pts}  numerics={nums}")
                    if isinstance(pts, (int, float)):
                        round_total += pts
            print(f"  Round {rnd} total: {round_total}")

    await context.storage_state(path=str(DEFAULT_SESSION_PATH))
    await browser.close()
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
