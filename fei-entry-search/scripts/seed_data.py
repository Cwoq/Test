#!/usr/bin/env python3
"""Seed the database with realistic historical FEI jumping show data.

This data is based on publicly known North American FEI jumping venues,
their typical show weeks, star levels, and approximate entry ranges.
Use this to demo the dashboard before running the live scrapers.
"""

import random
from datetime import date, timedelta

from src.db.database import get_session, init_db
from src.db.models import CompetitionClass, Show, Venue

# Realistic North American FEI jumping venues with typical characteristics
# Format: (name, state, city, country, slug, shows_per_year_data)
# shows_per_year_data: list of (week_range, star_level, base_entries, variance)
VENUES = [
    {
        "name": "Winter Equestrian Festival",
        "state": "FL", "city": "Wellington", "country": "USA",
        "slug": "wef",
        "shows": [
            # WEF runs weeks 1-12 approximately (Jan-Mar)
            (range(1, 13), [2, 3, 4, 5], 45, 15),
        ],
    },
    {
        "name": "Palm Beach International Equestrian Center",
        "state": "FL", "city": "Wellington", "country": "USA",
        "slug": "pbiec",
        "shows": [
            (range(1, 13), [2, 3], 38, 12),
        ],
    },
    {
        "name": "Tryon International Equestrian Center",
        "state": "NC", "city": "Mill Spring", "country": "USA",
        "slug": "tryon",
        "shows": [
            (range(14, 18), [2, 3], 25, 8),  # Spring
            (range(22, 30), [3, 4], 30, 10),  # Summer
            (range(36, 42), [2, 3], 22, 7),   # Fall
        ],
    },
    {
        "name": "Desert International Horse Park",
        "state": "CA", "city": "Thermal", "country": "USA",
        "slug": "dihp",
        "shows": [
            (range(2, 12), [2, 3], 28, 10),  # Winter circuit
        ],
    },
    {
        "name": "Blenheim EquiSports",
        "state": "CA", "city": "San Juan Capistrano", "country": "USA",
        "slug": "blenheim",
        "shows": [
            (range(14, 22), [2, 3], 22, 8),  # Spring
            (range(26, 36), [2, 3, 4], 26, 9),  # Summer
        ],
    },
    {
        "name": "Spruce Meadows",
        "state": "AB", "city": "Calgary", "country": "CAN",
        "slug": "sprucemeadows",
        "shows": [
            (range(23, 27), [4, 5], 50, 12),  # June National/North American
            (range(36, 38), [5], 55, 10),  # Masters
        ],
    },
    {
        "name": "Thunderbird Show Park",
        "state": "BC", "city": "Langley", "country": "CAN",
        "slug": "thunderbird",
        "shows": [
            (range(18, 22), [2, 3], 18, 6),  # Spring
            (range(30, 36), [2, 3], 20, 7),  # Summer
        ],
    },
    {
        "name": "HITS Saugerties",
        "state": "NY", "city": "Saugerties", "country": "USA",
        "slug": "hits",
        "shows": [
            (range(22, 28), [2, 3], 20, 8),  # Summer
            (range(36, 40), [3, 4], 28, 9),  # Fall
        ],
    },
    {
        "name": "Old Salem Farm",
        "state": "NY", "city": "North Salem", "country": "USA",
        "slug": "oldsalem",
        "shows": [
            (range(20, 23), [3], 32, 8),  # Spring
        ],
    },
    {
        "name": "Kentucky Spring Horse Show",
        "state": "KY", "city": "Lexington", "country": "USA",
        "slug": "kentuckyspring",
        "shows": [
            (range(18, 22), [2, 3], 22, 7),
        ],
    },
    {
        "name": "Split Rock Jumping Tour - Lexington",
        "state": "KY", "city": "Lexington", "country": "USA",
        "slug": "splitrock",
        "shows": [
            (range(20, 24), [3, 4], 24, 8),
            (range(40, 44), [3], 18, 6),  # Fall
        ],
    },
    {
        "name": "Traverse City Horse Shows",
        "state": "MI", "city": "Traverse City", "country": "USA",
        "slug": "traversecity",
        "shows": [
            (range(26, 32), [2, 3], 20, 7),  # Summer
        ],
    },
    {
        "name": "Live Oak International",
        "state": "FL", "city": "Ocala", "country": "USA",
        "slug": "liveoak",
        "shows": [
            (range(10, 12), [3], 28, 8),  # March
        ],
    },
    {
        "name": "Upperville Colt & Horse Show",
        "state": "VA", "city": "Upperville", "country": "USA",
        "slug": "upperville",
        "shows": [
            (range(23, 25), [2], 15, 5),  # June
        ],
    },
    {
        "name": "Angelstone Tournaments",
        "state": "ON", "city": "Rockwood", "country": "CAN",
        "slug": "angelstone",
        "shows": [
            (range(26, 34), [2, 3], 16, 5),  # Summer
        ],
    },
    {
        "name": "Sacramento International Horse Show",
        "state": "CA", "city": "Sacramento", "country": "USA",
        "slug": "sacramento",
        "shows": [
            (range(18, 20), [2], 14, 4),
        ],
    },
    {
        "name": "Sonoma Horse Park",
        "state": "CA", "city": "Petaluma", "country": "USA",
        "slug": "sonoma",
        "shows": [
            (range(22, 28), [2], 12, 4),  # Summer
        ],
    },
    {
        "name": "HITS Ocala Winter Circuit",
        "state": "FL", "city": "Ocala", "country": "USA",
        "slug": "hitsocala",
        "shows": [
            (range(2, 10), [2, 3], 24, 8),
        ],
    },
    {
        "name": "Colorado Horse Park",
        "state": "CO", "city": "Parker", "country": "USA",
        "slug": "coloradohp",
        "shows": [
            (range(26, 32), [2], 12, 4),  # Summer
        ],
    },
    {
        "name": "Caledon Equestrian Park",
        "state": "ON", "city": "Caledon", "country": "CAN",
        "slug": "caledon",
        "shows": [
            (range(24, 30), [2], 14, 5),  # Summer
        ],
    },
    {
        "name": "Silver Oak Jumper Tournament",
        "state": "VT", "city": "Woodstock", "country": "USA",
        "slug": "silveroak",
        "shows": [
            (range(30, 34), [2], 10, 3),  # Aug
        ],
    },
    {
        "name": "Tbird Summer Classic",
        "state": "BC", "city": "Langley", "country": "CAN",
        "slug": "tbird_summer",
        "shows": [
            (range(28, 32), [2], 15, 5),
        ],
    },
    {
        "name": "Pin Oak Charity Horse Show",
        "state": "TX", "city": "Katy", "country": "USA",
        "slug": "pinoak",
        "shows": [
            (range(12, 14), [2], 16, 5),  # March
        ],
    },
    {
        "name": "Lake Placid Horse Show",
        "state": "NY", "city": "Lake Placid", "country": "USA",
        "slug": "lakeplacid",
        "shows": [
            (range(26, 28), [2, 3], 22, 7),  # July
        ],
    },
    {
        "name": "Washington International Horse Show",
        "state": "DC", "city": "Washington", "country": "USA",
        "slug": "wihs",
        "shows": [
            (range(43, 45), [3, 4], 35, 8),  # October
        ],
    },
    {
        "name": "National Horse Show",
        "state": "KY", "city": "Lexington", "country": "USA",
        "slug": "nhs",
        "shows": [
            (range(44, 46), [4, 5], 40, 10),  # November
        ],
    },
]

# Ranking class templates for FEI jumping
RANKING_CLASS_TEMPLATES = {
    1: [
        ("CSI1* - 1.30m Ranking Class", "Table A", 130, True),
        ("CSI1* - 1.25m Two Phase", "Table A", 125, False),
        ("CSI1* - Grand Prix 1.35m", "Grand Prix", 135, True),
    ],
    2: [
        ("CSI2* - 1.35m Ranking Class", "Table A", 135, True),
        ("CSI2* - 1.40m Speed Class", "Speed (Table C)", 140, False),
        ("CSI2* - Grand Prix 1.45m", "Grand Prix", 145, True),
        ("CSI2* - 1.30m Welcome", "Table A", 130, False),
    ],
    3: [
        ("CSI3* - 1.45m Ranking Class", "Table A", 145, True),
        ("CSI3* - 1.40m Speed Class", "Speed (Table C)", 140, False),
        ("CSI3* - Grand Prix 1.50m", "Grand Prix", 150, True),
        ("CSI3* - 1.45m Welcome Stake", "Table A", 145, True),
    ],
    4: [
        ("CSI4* - 1.50m Ranking Class", "Table A", 150, True),
        ("CSI4* - 1.45m Speed Class", "Speed (Table C)", 145, False),
        ("CSI4* - Grand Prix 1.55m", "Grand Prix", 155, True),
        ("CSI4* - 1.50m Welcome Stake", "Table A", 150, True),
    ],
    5: [
        ("CSI5* - 1.55m Ranking Class", "Table A", 155, True),
        ("CSI5* - 1.50m Speed Derby", "Speed (Table C)", 150, False),
        ("CSI5* - Grand Prix 1.60m", "Grand Prix", 160, True),
        ("CSI5* - 1.55m LONGINES Ranking", "Ranking", 155, True),
    ],
}

YEARS = [2021, 2022, 2023, 2024, 2025]


def generate_entry_count(base: int, variance: int, year: int, trend: float = 0.0) -> int:
    """Generate a realistic entry count with some randomness and a year-over-year trend."""
    year_offset = (year - 2023) * trend  # trend per year from midpoint
    count = base + year_offset + random.gauss(0, variance)
    return max(3, int(round(count)))


def seed_database(db_path=None):
    init_db(db_path)
    session = get_session(db_path)

    try:
        # Clear existing data
        session.query(CompetitionClass).delete()
        session.query(Show).delete()
        session.query(Venue).delete()
        session.flush()

        total_shows = 0
        total_classes = 0

        for venue_data in VENUES:
            venue = Venue(
                name=venue_data["name"],
                state=venue_data["state"],
                city=venue_data["city"],
                country=venue_data["country"],
                showgrounds_slug=venue_data["slug"],
            )
            session.add(venue)
            session.flush()

            # Assign a random trend to each venue (-3 to +3 entries/year)
            venue_trend = random.uniform(-3.0, 3.0)

            for weeks, star_levels, base_entries, variance in venue_data["shows"]:
                for year in YEARS:
                    for week in weeks:
                        # Not every week necessarily has a show every year
                        # Simulate ~70% show occurrence per eligible week
                        if random.random() > 0.7:
                            continue

                        star = random.choice(star_levels)
                        start = date.fromisocalendar(year, week, 3)  # Wednesday
                        end = start + timedelta(days=4)  # Through Sunday

                        show = Show(
                            venue_id=venue.id,
                            name=f"{venue_data['name']} - Week {week} {year}",
                            year=year,
                            week_number=week,
                            start_date=start,
                            end_date=end,
                            star_level=star,
                            fei_event_id=f"FEI-{venue_data['slug']}-{year}-W{week}",
                            source="fei",
                        )
                        session.add(show)
                        session.flush()
                        total_shows += 1

                        # Add classes for this show
                        classes = RANKING_CLASS_TEMPLATES.get(star, RANKING_CLASS_TEMPLATES[2])
                        for class_name, class_type, height, is_ranking in classes:
                            entry_count = generate_entry_count(
                                base_entries, variance, year, trend=venue_trend
                            )
                            # Ranking classes tend to have more entries
                            if is_ranking:
                                entry_count = int(entry_count * random.uniform(0.9, 1.3))
                            # Grand Prix typically gets the most
                            if class_type == "Grand Prix":
                                entry_count = int(entry_count * random.uniform(1.0, 1.4))

                            starter_count = max(2, int(entry_count * random.uniform(0.85, 0.98)))

                            comp_class = CompetitionClass(
                                show_id=show.id,
                                name=class_name,
                                fei_class_type=class_type,
                                height_cm=height,
                                is_ranking_class=is_ranking,
                                entry_count=entry_count,
                                starter_count=starter_count,
                            )
                            session.add(comp_class)
                            total_classes += 1

        session.commit()
        print(f"Seeded {len(VENUES)} venues, {total_shows} shows, {total_classes} classes")
        print(f"Years: {YEARS[0]}-{YEARS[-1]}")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
