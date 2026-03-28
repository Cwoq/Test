#!/usr/bin/env python3
"""CLI script to scrape FEI calendar for jumping show entry data."""

import argparse
import asyncio
import logging
import sys
from datetime import date, timedelta

from src.scrapers.fei_calendar import FEICalendarScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape FEI jumping show data from data.fei.org"
    )
    parser.add_argument(
        "--start",
        type=date.fromisoformat,
        default=date.today() - timedelta(days=365 * 5),
        help="Start date (YYYY-MM-DD). Default: 5 years ago.",
    )
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        default=date.today(),
        help="End date (YYYY-MM-DD). Default: today.",
    )
    parser.add_argument(
        "--federations",
        nargs="+",
        default=["USA", "CAN", "MEX"],
        help="National federation codes. Default: USA CAN MEX",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Path to SQLite database. Default: data/fei_entries.db",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode (visible window) for debugging.",
    )
    return parser.parse_args()


async def run(args):
    async with FEICalendarScraper(headless=not args.headed) as scraper:
        await scraper.scrape_and_store(
            start_date=args.start,
            end_date=args.end,
            db_path=args.db,
        )


def main():
    args = parse_args()
    print(f"Scraping FEI calendar: {args.start} to {args.end}")
    print(f"Federations: {', '.join(args.federations)}")

    try:
        asyncio.run(run(args))
        print("Done! Data stored in database.")
    except KeyboardInterrupt:
        print("\nScraping interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
