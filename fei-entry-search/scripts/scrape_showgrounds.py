#!/usr/bin/env python3
"""CLI script to scrape ShowGrounds Live for jumping show entry data."""

import argparse
import asyncio
import logging
import sys

from src.scrapers.showgrounds import KNOWN_VENUES, ShowGroundsScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape ShowGrounds Live for jumping show entry data"
    )
    parser.add_argument(
        "--venues",
        nargs="+",
        default=None,
        help=f"Venue slugs to scrape. Default: all known venues. Available: {', '.join(KNOWN_VENUES.keys())}",
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
    parser.add_argument(
        "--list-venues",
        action="store_true",
        help="List all known venues and exit.",
    )
    return parser.parse_args()


async def run(args):
    async with ShowGroundsScraper(headless=not args.headed, venues=args.venues) as scraper:
        await scraper.scrape_and_store(venues=args.venues, db_path=args.db)


def main():
    args = parse_args()

    if args.list_venues:
        print("Known ShowGrounds Live venues:")
        for slug, info in KNOWN_VENUES.items():
            print(f"  {slug:20s} {info['name']} ({info.get('city', '')}, {info.get('state', '')})")
        return

    venues = args.venues or list(KNOWN_VENUES.keys())
    print(f"Scraping {len(venues)} venue(s): {', '.join(venues)}")

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
