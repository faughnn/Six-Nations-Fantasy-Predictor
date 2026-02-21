# Streamline Scraping — Design Document

**Date:** 2026-02-21
**Status:** Approved

## Problem

The current scraping workflow requires too much manual coordination:
- Multiple CLI commands to run each scraper individually
- Fantasy prices requires a two-step scrape + import process
- No visibility into when data was scraped or whether it's stale
- Dashboard status is inconsistent — shows present/missing booleans without timestamps
- No automated validation (e.g., squad completeness, pre-squad odds)
- Admin must mentally track what's been scraped and what needs re-scraping
- Fantasy stats scraper has no API endpoint — CLI only

## Solution

Enhance the existing scraping system with: a scrape history table, enriched status API with timestamps and validation warnings, a redesigned admin page as the single control point, and freshness indicators on public pages.

**Execution model:** Scraping runs locally via docker-compose only (Playwright not on Railway). The admin page at localhost:3000 triggers scraping on the local backend, which connects to Railway's Postgres.

## Design

### 1. Data Layer — `scrape_runs` Table

New table recording every scrape attempt:

| Column | Type | Description |
|--------|------|-------------|
| `id` | PK | Auto-increment |
| `season` | int | Season year |
| `round` | int | Round number |
| `market_type` | enum | `handicaps`, `totals`, `try_scorer`, `fantasy_prices`, `fantasy_stats` |
| `match_slug` | text (nullable) | Null for fantasy_prices/stats (which cover all matches) |
| `status` | enum | `in_progress`, `completed`, `failed`, `cancelled` |
| `started_at` | datetime | When the scrape began |
| `completed_at` | datetime (nullable) | When it finished |
| `duration_seconds` | float (nullable) | Elapsed time |
| `result_summary` | JSON | e.g., `{"players_found": 142, "matches_found": 3}` |
| `warnings` | JSON array | Validation warnings generated after this scrape |
| `error_message` | text (nullable) | Error details if failed |
| `created_at` | datetime | Row creation time |

Existing `scraped_at` fields on `MatchOdds`, `Odds`, and `FantasyPrice.created_at` remain unchanged — `scrape_runs` is supplementary tracking.

### 2. Backend API Changes

#### 2a. Enhanced Status Endpoint

`GET /api/matches/status` response enriched with per-market timestamps and validation:

```json
{
  "season": 2026,
  "round": 3,
  "matches": [
    {
      "home_team": "France",
      "away_team": "Ireland",
      "handicaps": { "status": "complete", "scraped_at": "2026-02-21T14:30:00Z" },
      "totals": { "status": "complete", "scraped_at": "2026-02-21T14:32:00Z" },
      "try_scorer": {
        "status": "warning",
        "scraped_at": "2026-02-19T10:00:00Z",
        "warning": "Scraped before squad announcement"
      },
      "squad_status": { "total": 20, "expected": 23, "unknown_availability": 3 }
    }
  ],
  "fantasy_prices": { "status": "complete", "scraped_at": "2026-02-20T18:00:00Z", "player_count": 142 },
  "fantasy_stats": { "status": "not_applicable", "note": "Round not yet played" },
  "warnings": [
    { "type": "pre_squad_odds", "match": "France v Ireland", "market": "try_scorer", "action": "re_scrape_try_scorer" },
    { "type": "incomplete_squad", "team": "Ireland", "count": 20, "expected": 23 }
  ],
  "last_scrape_run": { "market": "totals", "completed_at": "2026-02-21T14:32:00Z" },
  "scrape_history": []
}
```

#### 2b. New "Scrape All" Endpoint

`POST /api/scrape/all` — orchestrates everything in sequence:
1. Scrape handicaps (all matches)
2. Scrape totals (all matches)
3. Scrape try scorers (all matches)
4. Import fantasy prices
5. Run validation
6. Record all runs in `scrape_runs`

Returns a job ID with per-step progress reporting.

#### 2c. Fantasy Stats Scrape Endpoint

`POST /api/scrape/fantasy-stats` — triggers the stats scraper (currently CLI-only). Only runs post-round.

#### 2d. Merge Fantasy Two-Step Import

The `/api/scrape/import-prices` endpoint handles scrape + import in one operation. No intermediate JSON file from the user's perspective.

### 3. Admin Page Redesign (`/admin/scrape`)

The admin page becomes the scraping command center with four sections:

#### 3a. Control Panel (top)

- **"Scrape Everything" button** — primary, triggers `POST /api/scrape/all`. Shows progress overlay: "Step 1/5: Scraping handicaps... (2/3 matches done)"
- **Individual market buttons** — Handicaps, Totals, Try Scorers, Fantasy Prices, Fantasy Stats
- **Active job display** — real-time progress with cancel button

#### 3b. Round Status Grid (middle)

Per-match, per-market status table:

```
              | Handicaps      | Totals         | Try Scorers     | Squad
France v IRE  | ✓ 2h ago       | ✓ 2h ago       | ⚠ 2d ago (pre)  | 20/23 ⚠
England v WAL | ✓ 2h ago       | ✓ 2h ago       | ✓ 1h ago        | 23/23 ✓
Scotland v ITA| — missing      | — missing      | — missing       | 0/23

Fantasy Prices: ✓ Imported 3h ago (142 players)
Fantasy Stats:  — Round not yet played
```

Color coding:
- **Green**: Data present and fresh
- **Amber**: Data present but stale or has warnings (e.g., pre-squad odds)
- **Red**: Data missing
- **Gray**: Not applicable

Each cell is clickable — clicking an amber/red cell triggers a re-scrape for that market+match.

#### 3c. Warnings Panel

Actionable warnings with one-click re-scrape buttons:

```
⚠ Try scorer odds for France v Ireland scraped before squad release — [Re-scrape]
⚠ Ireland squad incomplete: 20/23 players — [Re-scrape Prices]
⚠ No data for Scotland v Italy — [Scrape All Markets]
```

#### 3d. Scrape History (collapsible)

Timeline of recent scrape runs:
```
14:32 — Totals: Completed (3 matches, 12s) ✓
14:30 — Handicaps: Completed (3 matches, 15s) ✓
Feb 19 — Try Scorers: Completed (3 matches, 45s) ⚠ Pre-squad
```

### 4. Public-Facing Freshness Indicators

Non-admin pages get lightweight data freshness info:

- **Dashboard**: Match cards show "last updated X ago" + caveat banners when relevant ("Some odds were retrieved before team announcements")
- **Try Scorers page**: Header shows "Odds retrieved: Feb 21, 14:30" with amber banner if pre-squad
- **General pattern**: Any page displaying scraped data gets a small freshness indicator

### 5. Validation Rules Engine

Automated checks that run after each scrape and populate `scrape_runs.warnings`:

| # | Rule | Trigger | Warning |
|---|------|---------|---------|
| 1 | Squad completeness | < 23 players for a team after prices import | "Ireland squad incomplete: 20/23" |
| 2 | Pre-squad odds | Try scorer odds scraped before squad availability data exists | "Try scorer odds may be outdated" |
| 3 | Stale odds | Any market data > 24h old | "Handicap odds are 2 days old" |
| 4 | Missing markets | Match has some but not all three odds types | "Scotland v Italy missing: totals" |
| 5 | Stats availability | Round played but no fantasy stats scraped | "Round 2 stats not yet scraped" |
| 6 | Availability unknown | Players with "unknown" availability after import | "15 players have unknown availability" |
| 7 | Missing player odds | Squad known (starting/sub) but player lacks try scorer odds | "3 Ireland players missing try scorer odds" |
| 8 | Suspiciously few odds | Try scorer scrape returns < 20 players for a match | "Only 12 players with odds — possible partial scrape" |
| 9 | Too few bookmakers | Market scrape finds < 3 bookmakers | "Only 2 bookmakers found — data may be unreliable" |
| 10 | Odds outlier | A player's odds have extreme variance across bookmakers | "Unusual odds variance for Player X" |
| 11 | Session health | Fantasy scrape returns significantly fewer players than previous | "Only 80 players found (vs 142 last round) — session issue?" |
| 12 | Zero-data scrape | Scrape completes with no data | "Handicaps scrape returned no data" |
| 13 | Match count mismatch | Expected N matches, found fewer | "Only 2 matches found (expected 3)" |

Each warning includes an `action` field mapping to a specific re-scrape button.

## Out of Scope

- Scheduled/automatic scraping (no cron or background scheduler)
- Running scraping on Railway production (stays local-only)
- Price change detection across scrape runs
