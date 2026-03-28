# FEI Low Entry Show Search

Find FEI jumping shows in North America with historically low entry numbers in ranking classes. Target shows where fewer competitors enter to maximize your opportunity for ranking points.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Scrape historical data (FEI calendar - primary source)
python scripts/scrape_fei.py --start 2023-01-01 --end 2025-12-31

# Scrape ShowGrounds Live data (supplementary)
python scripts/scrape_showgrounds.py

# Launch the dashboard
python -m src.web.app
# Open http://localhost:5000
```

## Features

- **Dashboard**: Filter and sort shows by star level, state, week range. Sorted by lowest avg entries in ranking classes.
- **Calendar Heatmap**: 52-week grid color-coded by entry density. Green = low entries (opportunity), Red = crowded.
- **Show Detail**: Year-over-year history for a specific venue with trend charts.
- **Sortable Columns**: Click any table header to sort.

## Data Sources

- **FEI Database** (data.fei.org) — Official calendar, results, and entry counts
- **ShowGrounds Live** (showgroundslive.com) — US show management platform with class/entry data

## Scraper CLI Options

```bash
# FEI Scraper
python scripts/scrape_fei.py --start 2024-01-01 --end 2024-12-31 --federations USA CAN
python scripts/scrape_fei.py --headed  # visible browser for debugging

# ShowGrounds Scraper
python scripts/scrape_showgrounds.py --venues pbiec tryon blenheim
python scripts/scrape_showgrounds.py --list-venues  # see all known venues
```

## Project Structure

```
src/
├── db/           # SQLAlchemy models (Venue, Show, CompetitionClass) + database setup
├── scrapers/     # Playwright-based scrapers for FEI and ShowGrounds
├── analysis/     # Entry count aggregation, trend calculation, ranking logic
└── web/          # Flask dashboard with templates and static assets
scripts/          # CLI entry points for running scrapers
```
