"""
Find total player count by checking per-round rankings of all league members.

Navigates through the rankings page, clicking on each league to get the real
member list, then fetches per-round progression for each member.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.scrapers.fantasy_sixnations import DEFAULT_SESSION_PATH

BASE_URL = "https://fantasy.sixnationsrugby.com"
DATA_DIR = Path(__file__).parent / "data"
MY_IDJG = "322902"


async def api_fetch(page, endpoint):
    """Make an authenticated API call from within the browser context."""
    return await page.evaluate(
        """async (endpoint) => {
            const token = localStorage.getItem('jwtToken600') || '';
            const resp = await fetch(endpoint, {
                credentials: 'include',
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

    session_path = DEFAULT_SESSION_PATH
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    )
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        no_viewport=True,
        storage_state=str(session_path),
    )
    page = await context.new_page()

    # Intercept API responses
    api_responses = {}

    async def on_resp(response):
        url = response.url
        if "/v1/private/classementgeneral/" in url:
            try:
                body = await response.text()
                api_responses[url] = body
            except Exception:
                pass

    page.on("response", on_resp)

    try:
        print("Loading site...")
        await page.goto(f"{BASE_URL}/m6n/#/game/play/me", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4)

        # Dismiss overlays
        for sel in ['button:has-text("Accept")', 'button:has-text("Accept All")', '#onetrust-accept-btn-handler']:
            try:
                elem = await page.query_selector(sel)
                if elem and await elem.is_visible():
                    await elem.click()
                    await asyncio.sleep(1)
            except Exception:
                pass
        await asyncio.sleep(2)

        # Step 1: Go to rankings page
        print("\n1. Going to rankings page...")
        await page.goto(f"{BASE_URL}/m6n/#/game/rankings", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)

        # Get the list of league tabs visible on rankings page
        league_tabs = await page.evaluate(r"""() => {
            const tabs = [];
            // Look for league name elements in the rankings page
            document.querySelectorAll('[class*="groupe"], [class*="league"], [class*="onglet"], .ctr-tab-item, .mat-mdc-tab').forEach(el => {
                const text = el.innerText ? el.innerText.trim() : '';
                if (text && text.length > 2 && text.length < 80) {
                    tabs.push(text);
                }
            });
            // Also look for clickable items that contain league names
            document.querySelectorAll('button, a, [role="tab"], span').forEach(el => {
                const text = el.innerText ? el.innerText.trim() : '';
                if (text && text.length > 2 && text.length < 80 && el.offsetParent !== null) {
                    if (/league|fantasy|reddit|classic|nianna|rampager/i.test(text)) {
                        tabs.push(text);
                    }
                }
            });
            return [...new Set(tabs)];
        }""")
        print(f"  League tabs found: {league_tabs}")

        # Step 2: Get leagues via API
        print("\n2. Fetching leagues list...")
        leagues_data = await api_fetch(page, "/v1/private/mesgroupes?lg=en")
        if isinstance(leagues_data, dict) and "_error" in leagues_data:
            print(f"  ERROR: {leagues_data['_error']}")
            return

        leagues = leagues_data if isinstance(leagues_data, list) else leagues_data.get("groupes", leagues_data.get("leagues", []))
        print(f"  Found {len(leagues)} leagues")

        # Step 3: Click on each league tab and capture the API response
        all_members = {}
        league_info = []

        for lg in leagues:
            league_id = lg.get("idg", lg.get("id"))
            league_name = lg.get("nom", lg.get("name", f"League {league_id}"))
            print(f"\n3. Clicking on '{league_name}' (id={league_id})...")

            api_responses.clear()

            # Try to click the league by matching text
            clicked = False
            # Try exact text match first
            for selector in [
                f'text="{league_name}"',
                f'text="{league_name.upper()}"',
                f':text("{league_name}")',
            ]:
                try:
                    elem = await page.query_selector(selector)
                    if elem and await elem.is_visible():
                        await elem.click()
                        clicked = True
                        break
                except Exception:
                    pass

            if not clicked:
                # Try partial text match
                try:
                    # Use a substring for matching
                    short_name = league_name[:20]
                    elems = await page.query_selector_all(f'text=/{short_name}/i')
                    for elem in elems:
                        if await elem.is_visible():
                            await elem.click()
                            clicked = True
                            break
                except Exception:
                    pass

            if not clicked:
                print(f"  Could not find clickable element for '{league_name}', trying API directly...")
                # Fallback: call API directly
                await api_fetch(page, f"/v1/private/usergroup/{league_id}/{MY_IDJG}?lg=en")
                await asyncio.sleep(0.3)
                await api_fetch(page, "/v1/private/infosgame?lg=en")
                await asyncio.sleep(0.3)
                data = await api_fetch(page, f"/v1/private/classementgeneral/{league_id}?lg=en")
                if isinstance(data, dict) and "_error" not in data:
                    api_responses[f"direct_{league_id}"] = json.dumps(data)

            await asyncio.sleep(3)

            # Parse the classementgeneral response
            standings = None
            for url, body in api_responses.items():
                if "classementgeneral" in url:
                    try:
                        standings = json.loads(body)
                    except Exception:
                        pass
                    break

            # Also check direct fallback
            if standings is None:
                for url, body in api_responses.items():
                    if url.startswith("direct_"):
                        try:
                            standings = json.loads(body)
                        except Exception:
                            pass
                        break

            if standings is None:
                print(f"  No standings data captured for '{league_name}'")
                continue

            members = standings.get("joueurs", [])
            my_entry = standings.get("suivants", [])
            if isinstance(my_entry, list):
                members = members + my_entry
            elif isinstance(my_entry, dict):
                members.append(my_entry)

            # Deduplicate by idjg
            seen = set()
            unique_members = []
            for m in members:
                idjg = m.get("idjg")
                if idjg and idjg not in seen:
                    seen.add(idjg)
                    unique_members.append(m)

            print(f"  Found {len(unique_members)} members")

            league_info.append({
                "id": league_id,
                "name": league_name,
                "member_count": len(unique_members),
                "members": [
                    {
                        "idjg": m.get("idjg"),
                        "manager": m.get("manager", "").strip(),
                        "team": m.get("equipe", ""),
                        "position": m.get("position", ""),
                        "points": m.get("totaljoueur", ""),
                    }
                    for m in unique_members
                ],
            })

            for m in unique_members:
                idjg = m.get("idjg")
                if idjg not in all_members:
                    all_members[idjg] = {
                        "idjg": idjg,
                        "manager": m.get("manager", "").strip(),
                        "team": m.get("equipe", ""),
                        "overall_position": m.get("position", ""),
                        "overall_points": m.get("totaljoueur", ""),
                        "leagues": [],
                    }
                all_members[idjg]["leagues"].append(league_name)

        # Step 4: For each unique member, fetch their per-round progression
        print(f"\n4. Fetching per-round progression for {len(all_members)} unique members...")
        highest_rank_seen = 0
        highest_rank_player = None
        highest_rank_round = None

        for i, (idjg, member) in enumerate(all_members.items()):
            prog = await api_fetch(page, f"/v1/private/progressionjoueur/1/{idjg}?lg=en")
            if isinstance(prog, dict) and "_error" in prog:
                print(f"  [{i+1}/{len(all_members)}] {member['manager']} - ERROR: {prog['_error']}")
                member["progression"] = []
                member["worst_rank"] = None
                member["worst_round"] = None
                continue

            rounds_data = prog.get("positionJournees", []) if isinstance(prog, dict) else []

            worst_rank = 0
            worst_round = None
            round_ranks = []

            for rd in rounds_data:
                if isinstance(rd, dict):
                    rank = rd.get("position_general", 0)
                    round_num = rd.get("numero", rd.get("journee", "?"))
                    try:
                        rank = int(rank)
                    except (ValueError, TypeError):
                        rank = 0
                    round_ranks.append({"round": round_num, "rank": rank})
                    if rank > worst_rank:
                        worst_rank = rank
                        worst_round = round_num

            member["progression"] = round_ranks
            member["worst_rank"] = worst_rank
            member["worst_round"] = worst_round

            if worst_rank > highest_rank_seen:
                highest_rank_seen = worst_rank
                highest_rank_player = member["manager"]
                highest_rank_round = worst_round

            rank_str = f"worst rank: {worst_rank:,}" if worst_rank > 0 else "no rank data"
            print(f"  [{i+1}/{len(all_members)}] {member['manager']:30s} {rank_str:>20s}  R1={round_ranks[0]['rank'] if len(round_ranks) > 0 else '?':>7,}  R2={round_ranks[1]['rank'] if len(round_ranks) > 1 else '?':>7,}  R3={round_ranks[2]['rank'] if len(round_ranks) > 2 else '?':>7,}")

            await asyncio.sleep(0.3)

        # Step 5: Print results
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)

        print(f"\nHighest rank number seen: {highest_rank_seen:,}")
        print(f"  -> At least {highest_rank_seen:,} players in the game")
        print(f"  Found on: {highest_rank_player} (Round {highest_rank_round})")

        for lg in league_info:
            print(f"\n{'-' * 90}")
            print(f"League: {lg['name']} ({lg['member_count']} members)")
            print(f"{'-' * 90}")
            print(f"{'Pos':<5} {'Team':<28} {'Manager':<22} {'Pts':<8} {'Worst Rank':<14} {'Rnd':<4}")
            print(f"{'-'*5} {'-'*28} {'-'*22} {'-'*8} {'-'*14} {'-'*4}")

            sorted_members = sorted(
                lg["members"],
                key=lambda m: int(m["position"]) if str(m.get("position", "")).isdigit() else 999999,
            )

            for m in sorted_members:
                idjg = m["idjg"]
                member_data = all_members.get(idjg, {})
                worst = member_data.get("worst_rank")
                worst_str = f"{worst:,}" if worst else "N/A"
                worst_round = member_data.get("worst_round", "")
                print(
                    f"{m['position']:<5} {m['team'][:28]:<28} {m['manager'][:22]:<22} "
                    f"{m['points']:<8} {worst_str:<14} {worst_round}"
                )

        # Save full data
        output = {
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "total_unique_members_checked": len(all_members),
            "highest_rank_seen": highest_rank_seen,
            "minimum_total_players": highest_rank_seen,
            "highest_rank_player": highest_rank_player,
            "highest_rank_round": highest_rank_round,
            "leagues": league_info,
            "members": {
                idjg: {
                    "manager": m["manager"],
                    "team": m["team"],
                    "overall_position": m["overall_position"],
                    "overall_points": m["overall_points"],
                    "leagues": m["leagues"],
                    "worst_rank": m["worst_rank"],
                    "worst_round": m["worst_round"],
                    "progression": m["progression"],
                }
                for idjg, m in all_members.items()
            },
        }

        output_path = DATA_DIR / "league_member_rankings.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {output_path}")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await context.storage_state(path=str(session_path))
        await browser.close()
        await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
