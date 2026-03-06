# Hourly Scrape via GitHub Actions

## Problem

Player analysis data (try scorer odds, fantasy prices/ownership) goes stale between manual scrapes. We want automatic hourly refreshes on match-week days.

## Solution

A GitHub Actions workflow that runs hourly on specific dates, scraping try scorer odds and fantasy prices/ownership, writing directly to the Railway production database.

## Schedule

Runs every hour on match-week days only:

- **Round 4**: March 4, 5, 6, 7
- **Round 5**: March 12, 13, 14

After March 14 the tournament is over.

## Workflow Steps

1. Checkout repo
2. Install Python dependencies + Playwright + Chromium
3. Decode `SESSION_STATE` secret to `backend/data/session_state.json`
4. Auto-detect current round via `get_current_round()` from `app/fixtures.py`
5. Run `scrape_oddschecker_tryscorer.py --save-db --season 2026 --round <N>`
6. Run `scrape_fantasy_prices.py --season 2026 --round <N>` (headless, using saved session)
7. Import scraped fantasy JSON to DB

## GitHub Secrets Required

- `DATABASE_URL` — Railway Postgres connection string (the `postgresql+asyncpg://...` URL)
- `JWT_SECRET` — set to `dummy-local-scraper`
- `SESSION_STATE` — base64-encoded contents of `backend/data/session_state.json`

## Round Detection

Uses the existing `get_current_round()` function from `backend/app/fixtures.py`, which returns the earliest round with unplayed matches based on the hardcoded schedule.

## Constraints

- Scrapers use Playwright (headless Chromium) — GitHub Actions provides this via `playwright install chromium`
- Fantasy prices scraper requires a valid session token (JWT expires April 6, covers the whole tournament)
- Oddschecker scraper needs no auth
- Both scrapers already support headless mode
