"""
Push locally-scraped data to the production Railway database.

Usage:
    python push_to_production.py --season 2026 --round 4           # dry-run
    python push_to_production.py --season 2026 --round 4 --push    # actually sync

Requires PROD_DATABASE_URL env var pointing to Railway Postgres.
Reads from local Docker Postgres at localhost:5432.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


LOCAL_DB_URL = "postgresql+asyncpg://rugby:rugbypass@localhost:5432/fantasy_rugby"

# Columns to sync per table (excluding id and player_id which need remapping)
MATCH_ODDS_COLS = [
    "season", "round", "match_date", "home_team", "away_team",
    "home_win", "away_win", "draw",
    "over_under_line", "over_odds", "under_odds",
    "handicap_line", "home_handicap_odds", "away_handicap_odds",
    "scraped_at",
]

ODDS_COLS = [
    "player_id", "season", "round", "match_date",
    "anytime_try_scorer", "first_try_scorer", "two_plus_tries",
    "player_of_match", "scraped_at", "source",
]

FANTASY_PRICES_COLS = [
    "player_id", "season", "round",
    "price", "ownership_pct", "availability", "created_at",
]


def get_prod_url() -> str:
    url = os.environ.get("PROD_DATABASE_URL", "")
    if not url:
        print("ERROR: Set PROD_DATABASE_URL environment variable.")
        print("  export PROD_DATABASE_URL=\"postgresql+asyncpg://postgres:...@shinkansen.proxy.rlwy.net:25878/railway\"")
        sys.exit(1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


async def fetch_rows(session: AsyncSession, query: str, params: dict) -> list[dict]:
    result = await session.execute(text(query), params)
    columns = result.keys()
    return [dict(zip(columns, row)) for row in result.fetchall()]


async def run(season: int, round_num: int, push: bool):
    prod_url = get_prod_url()
    local_engine = create_async_engine(LOCAL_DB_URL, echo=False)
    prod_engine = create_async_engine(prod_url, echo=False)
    LocalSession = async_sessionmaker(local_engine, class_=AsyncSession, expire_on_commit=False)
    ProdSession = async_sessionmaker(prod_engine, class_=AsyncSession, expire_on_commit=False)

    params = {"season": season, "round": round_num}

    # --- Read local data ---
    async with LocalSession() as local:
        local_match_odds = await fetch_rows(local,
            "SELECT * FROM match_odds WHERE season = :season AND round = :round", params)

        local_odds = await fetch_rows(local,
            "SELECT * FROM odds WHERE season = :season AND round = :round", params)

        local_prices = await fetch_rows(local,
            "SELECT * FROM fantasy_prices WHERE season = :season AND round = :round", params)

        # Collect all local player_ids referenced
        player_ids = set()
        for row in local_odds:
            player_ids.add(row["player_id"])
        for row in local_prices:
            player_ids.add(row["player_id"])

        # Fetch those players
        local_players = {}
        if player_ids:
            placeholders = ", ".join(f":pid_{i}" for i in range(len(player_ids)))
            pid_params = {f"pid_{i}": pid for i, pid in enumerate(player_ids)}
            rows = await fetch_rows(local,
                f"SELECT id, name, country, fantasy_position, is_kicker FROM players WHERE id IN ({placeholders})",
                pid_params)
            for r in rows:
                local_players[r["id"]] = r

    print(f"\n{'='*60}")
    print(f"  Push to Production — Season {season}, Round {round_num}")
    print(f"{'='*60}")
    print(f"\n  Local data found:")
    print(f"    match_odds:     {len(local_match_odds)} rows")
    print(f"    odds:           {len(local_odds)} rows")
    print(f"    fantasy_prices: {len(local_prices)} rows")
    print(f"    players ref'd:  {len(local_players)} unique")

    if not local_match_odds and not local_odds and not local_prices:
        print("\n  Nothing to sync. Exiting.")
        await local_engine.dispose()
        await prod_engine.dispose()
        return

    # --- Build player ID mapping (local_id -> prod_id) ---
    async with ProdSession() as prod:
        # Fetch all production players for matching
        prod_players = await fetch_rows(prod,
            "SELECT id, name, country FROM players", {})

    # Build lookup by (lowercase name, lowercase country)
    prod_lookup: dict[tuple[str, str], int] = {}
    for p in prod_players:
        key = (p["name"].strip().lower(), p["country"].strip().lower())
        prod_lookup[key] = p["id"]

    id_map: dict[int, int] = {}  # local_id -> prod_id
    missing_players: list[dict] = []

    for local_id, player in local_players.items():
        key = (player["name"].strip().lower(), player["country"].strip().lower())
        if key in prod_lookup:
            id_map[local_id] = prod_lookup[key]
        else:
            missing_players.append(player)

    if missing_players:
        print(f"\n  Players not found in production ({len(missing_players)}):")
        for p in missing_players:
            print(f"    - {p['name']} ({p['country']})")

    if not push:
        print(f"\n  Player mapping: {len(id_map)}/{len(local_players)} matched")
        if missing_players:
            print(f"  {len(missing_players)} players would be CREATED in production")
        print(f"\n  DRY RUN — no changes made. Add --push to sync.\n")
        await local_engine.dispose()
        await prod_engine.dispose()
        return

    # --- Push mode: create missing players, then upsert data ---
    async with ProdSession() as prod:
        async with prod.begin():
            # Create missing players
            for player in missing_players:
                result = await prod.execute(text(
                    "INSERT INTO players (name, country, fantasy_position, is_kicker, created_at, updated_at) "
                    "VALUES (:name, :country, :position, :kicker, :now, :now) RETURNING id"
                ), {
                    "name": player["name"],
                    "country": player["country"],
                    "position": player["fantasy_position"],
                    "kicker": player["is_kicker"],
                    "now": datetime.utcnow(),
                })
                new_id = result.scalar_one()
                id_map[player["id"]] = new_id
                print(f"  Created player: {player['name']} ({player['country']}) -> prod id {new_id}")

            # Upsert match_odds
            mo_count = 0
            for row in local_match_odds:
                await prod.execute(text("""
                    INSERT INTO match_odds (season, round, match_date, home_team, away_team,
                        home_win, away_win, draw,
                        over_under_line, over_odds, under_odds,
                        handicap_line, home_handicap_odds, away_handicap_odds, scraped_at)
                    VALUES (:season, :round, :match_date, :home_team, :away_team,
                        :home_win, :away_win, :draw,
                        :over_under_line, :over_odds, :under_odds,
                        :handicap_line, :home_handicap_odds, :away_handicap_odds, :scraped_at)
                    ON CONFLICT ON CONSTRAINT uq_match_odds_season_round_teams
                    DO UPDATE SET
                        match_date = EXCLUDED.match_date,
                        home_win = EXCLUDED.home_win, away_win = EXCLUDED.away_win, draw = EXCLUDED.draw,
                        over_under_line = EXCLUDED.over_under_line,
                        over_odds = EXCLUDED.over_odds, under_odds = EXCLUDED.under_odds,
                        handicap_line = EXCLUDED.handicap_line,
                        home_handicap_odds = EXCLUDED.home_handicap_odds,
                        away_handicap_odds = EXCLUDED.away_handicap_odds,
                        scraped_at = EXCLUDED.scraped_at
                """), {col: row[col] for col in MATCH_ODDS_COLS})
                mo_count += 1

            # Upsert odds (with player_id remapping)
            odds_count = 0
            odds_skipped = 0
            for row in local_odds:
                prod_pid = id_map.get(row["player_id"])
                if prod_pid is None:
                    odds_skipped += 1
                    continue
                params_row = {col: row[col] for col in ODDS_COLS}
                params_row["player_id"] = prod_pid
                await prod.execute(text("""
                    INSERT INTO odds (player_id, season, round, match_date,
                        anytime_try_scorer, first_try_scorer, two_plus_tries,
                        player_of_match, scraped_at, source)
                    VALUES (:player_id, :season, :round, :match_date,
                        :anytime_try_scorer, :first_try_scorer, :two_plus_tries,
                        :player_of_match, :scraped_at, :source)
                    ON CONFLICT ON CONSTRAINT uq_odds_player_season_round
                    DO UPDATE SET
                        match_date = EXCLUDED.match_date,
                        anytime_try_scorer = EXCLUDED.anytime_try_scorer,
                        first_try_scorer = EXCLUDED.first_try_scorer,
                        two_plus_tries = EXCLUDED.two_plus_tries,
                        player_of_match = EXCLUDED.player_of_match,
                        scraped_at = EXCLUDED.scraped_at,
                        source = EXCLUDED.source
                """), params_row)
                odds_count += 1

            # Upsert fantasy_prices (with player_id remapping)
            fp_count = 0
            fp_skipped = 0
            for row in local_prices:
                prod_pid = id_map.get(row["player_id"])
                if prod_pid is None:
                    fp_skipped += 1
                    continue
                params_row = {col: row[col] for col in FANTASY_PRICES_COLS}
                params_row["player_id"] = prod_pid
                await prod.execute(text("""
                    INSERT INTO fantasy_prices (player_id, season, round,
                        price, ownership_pct, availability, created_at)
                    VALUES (:player_id, :season, :round,
                        :price, :ownership_pct, :availability, :created_at)
                    ON CONFLICT ON CONSTRAINT uq_player_season_round
                    DO UPDATE SET
                        price = EXCLUDED.price,
                        ownership_pct = EXCLUDED.ownership_pct,
                        availability = EXCLUDED.availability,
                        created_at = EXCLUDED.created_at
                """), params_row)
                fp_count += 1

    print(f"\n  Synced to production:")
    print(f"    match_odds:     {mo_count} upserted")
    print(f"    odds:           {odds_count} upserted" +
          (f" ({odds_skipped} skipped — unmapped player)" if odds_skipped else ""))
    print(f"    fantasy_prices: {fp_count} upserted" +
          (f" ({fp_skipped} skipped — unmapped player)" if fp_skipped else ""))
    print(f"\n  Done!\n")

    await local_engine.dispose()
    await prod_engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Push local scrape data to production DB")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--push", action="store_true", help="Actually sync (default is dry-run)")
    args = parser.parse_args()

    asyncio.run(run(args.season, args.round, args.push))


if __name__ == "__main__":
    main()
