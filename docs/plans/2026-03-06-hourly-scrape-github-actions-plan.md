# Hourly Scrape GitHub Actions Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automatically scrape try scorer odds and fantasy prices/ownership hourly on match-week days via GitHub Actions.

**Architecture:** A single GitHub Actions workflow with a cron schedule runs on specific match-week dates. It installs Playwright, restores the fantasy session from a secret, auto-detects the current round, runs both scrapers, and imports fantasy data to the production DB.

**Tech Stack:** GitHub Actions, Python, Playwright, existing scrapers

---

### Task 1: Add --headless flag to scrape_fantasy_prices.py

**Files:**
- Modify: `backend/scrape_fantasy_prices.py`

**Step 1: Add --headless argument to argparse**

In `scrape_fantasy_prices.py`, add a `--headless` flag and pass it to `FantasySixNationsScraper`:

```python
parser.add_argument(
    "--headless",
    action="store_true",
    help="Run in headless mode (requires saved session)",
)
```

And change the scraper instantiation from:
```python
scraper = FantasySixNationsScraper()
```
to:
```python
scraper = FantasySixNationsScraper(headless=args.headless)
```

**Step 2: Verify it still works**

Run: `cd backend && python scrape_fantasy_prices.py --help`
Expected: `--headless` appears in help output

**Step 3: Commit**

```bash
git add backend/scrape_fantasy_prices.py
git commit -m "feat: add --headless flag to fantasy prices scraper"
```

---

### Task 2: Create the helper script for CI

**Files:**
- Create: `backend/scrape_hourly.py`

A single Python script that:
1. Auto-detects the current round
2. Runs the try scorer scraper
3. Runs the fantasy prices scraper (headless)
4. Imports the resulting JSON to the DB

This avoids complex shell scripting in the workflow YAML.

**Step 1: Write the script**

The script should:
- Import `get_current_round` from `app.fixtures`
- Run `scrape_oddschecker_tryscorer.py --save-db --season 2026 --round N`
- Run `scrape_fantasy_prices.py --headless --season 2026 --round N --output data/fantasy_players_rN.json`
- Import via `import_scraped_json`
- Exit non-zero if any step fails, but continue to next step

**Step 2: Commit**

```bash
git add backend/scrape_hourly.py
git commit -m "feat: add hourly scrape orchestrator script for CI"
```

---

### Task 3: Create the GitHub Actions workflow

**Files:**
- Create: `.github/workflows/hourly-scrape.yml`

**Step 1: Write the workflow**

Key details:
- Cron: runs every hour on March 4-7 and March 12-14 2026
- Cron doesn't support specific dates, so run hourly and use a date-check step to skip off-days
- Uses `ubuntu-latest`
- Installs Python 3.11, pip dependencies from `backend/requirements.txt`
- Installs Playwright Chromium
- Decodes `SESSION_STATE` secret to `backend/data/session_state.json`
- Sets `DATABASE_URL` and `JWT_SECRET` env vars from secrets
- Runs `backend/scrape_hourly.py`
- Also supports manual trigger via `workflow_dispatch` with round input

**Step 2: Commit**

```bash
git add .github/workflows/hourly-scrape.yml
git commit -m "feat: add hourly scrape GitHub Actions workflow"
```

---

### Task 4: Final commit and push

**Step 1: Push to main**

```bash
git push
```

Railway auto-deploys but the workflow only runs in GitHub Actions — no impact on the deployed app.
