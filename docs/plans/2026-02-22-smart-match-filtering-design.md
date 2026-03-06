# Smart Match Filtering for Scraping

## Problem

When scraping odds for a partially-completed round (e.g. 2 of 3 matches played), the system:
1. Scrapes stale/useless odds for already-played matches
2. Shows stale-odds warnings for matches that are already finished
3. Provides no visual distinction between played and upcoming matches

## Solution

Hardcode the 2026 Six Nations fixture schedule with exact kickoff datetimes. A match is "played" if `now > kickoff + 2 hours`. This drives three behaviors:

### 1. Backend fixtures module (`app/fixtures.py`)

- Dict mapping `(season, round, home_team, away_team)` → kickoff UTC datetime
- Helper: `is_match_played(season, round, home, away) -> bool`
- Helper: `get_upcoming_matches(season, round) -> list` (filters out played)

### 2. Skip played matches during bulk scraping

In `_run_scraper()` and `_run_scrape_all()` in `app/api/scrape.py`:
- After match discovery, filter out played matches
- Log/report which matches were skipped
- Explicit single-match scrapes (match-market endpoint) still work — no filtering

### 3. Suppress warnings for played matches

In `validation_service.py`:
- Accept `played_matches` set parameter
- Skip all warning rules for matches in that set
- The `/api/matches/status` endpoint passes this info through

### 4. Frontend: visual treatment for played matches

- Add `is_played` boolean to `EnrichedMatchScrapeStatus` schema
- Admin UI greys out played match rows
- Disable per-cell scrape buttons for played matches

## Schedule Data

2026 Six Nations (all times UTC):

| Round | Date | Kickoff | Match |
|-------|------|---------|-------|
| 1 | Thu 5 Feb | 20:10 | France v Ireland |
| 1 | Sat 7 Feb | 14:10 | Italy v Scotland |
| 1 | Sat 7 Feb | 16:40 | England v Wales |
| 2 | Sat 14 Feb | 14:10 | Ireland v Italy |
| 2 | Sat 14 Feb | 16:40 | Scotland v England |
| 2 | Sun 15 Feb | 15:10 | Wales v France |
| 3 | Sat 21 Feb | 14:10 | England v Ireland |
| 3 | Sat 21 Feb | 16:40 | Wales v Scotland |
| 3 | Sun 22 Feb | 15:10 | France v Italy |
| 4 | Fri 6 Mar | 20:10 | Ireland v Wales |
| 4 | Sat 7 Mar | 14:10 | Scotland v France |
| 4 | Sat 7 Mar | 16:40 | Italy v England |
| 5 | Sat 14 Mar | 14:10 | Ireland v Scotland |
| 5 | Sat 14 Mar | 16:40 | Wales v Italy |
| 5 | Sat 14 Mar | 20:10 | France v England |
