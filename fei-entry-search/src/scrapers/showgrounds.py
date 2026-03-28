import logging
import re
from datetime import date, datetime

from playwright.async_api import Page

from src.db.database import get_session, init_db
from src.db.models import CompetitionClass, Show, Venue

from .base import BaseScraper

logger = logging.getLogger(__name__)

# Known ShowGrounds Live venue subdomains with their metadata
KNOWN_VENUES = {
    "pbiec": {"name": "Palm Beach International Equestrian Center", "state": "FL", "city": "Wellington", "country": "USA"},
    "tryon": {"name": "Tryon International Equestrian Center", "state": "NC", "city": "Mill Spring", "country": "USA"},
    "blenheim": {"name": "Blenheim EquiSports", "state": "CA", "city": "San Juan Capistrano", "country": "USA"},
    "hits": {"name": "HITS", "state": "NY", "city": "Saugerties", "country": "USA"},
    "dihp": {"name": "Desert International Horse Park", "state": "CA", "city": "Thermal", "country": "USA"},
    "kentuckyspring": {"name": "Kentucky Spring Horse Show", "state": "KY", "city": "Lexington", "country": "USA"},
    "splitrock": {"name": "Split Rock Jumping Tour", "state": "KY", "city": "Lexington", "country": "USA"},
    "thunderbird": {"name": "Thunderbird Show Park", "state": "BC", "city": "Langley", "country": "CAN"},
    "sprucemeadows": {"name": "Spruce Meadows", "state": "AB", "city": "Calgary", "country": "CAN"},
    "traversecity": {"name": "Traverse City Horse Shows", "state": "MI", "city": "Traverse City", "country": "USA"},
    "upperville": {"name": "Upperville Colt & Horse Show", "state": "VA", "city": "Upperville", "country": "USA"},
    "lakewood": {"name": "Lakewood Horse Show", "state": "FL", "city": "Ocala", "country": "USA"},
    "wef": {"name": "Winter Equestrian Festival", "state": "FL", "city": "Wellington", "country": "USA"},
    "oldSalem": {"name": "Old Salem Farm", "state": "NY", "city": "North Salem", "country": "USA"},
    "sonoma": {"name": "Sonoma Horse Park", "state": "CA", "city": "Petaluma", "country": "USA"},
}

# Patterns indicating FEI jumping classes on ShowGrounds
FEI_CLASS_PATTERNS = [
    r"CSI\d?\*",
    r"Grand Prix",
    r"FEI",
    r"\$\d+[,\d]*\s*(Grand Prix|GP)",
    r"Ranking\s*Class",
    r"World Cup",
    r"Nations Cup",
]


def _is_fei_class(name: str) -> bool:
    return any(re.search(p, name, re.IGNORECASE) for p in FEI_CLASS_PATTERNS)


class ShowGroundsScraper(BaseScraper):
    """Scrapes ShowGrounds Live for jumping show entry data."""

    def __init__(self, headless: bool = True, venues: list[str] | None = None):
        super().__init__(headless=headless, min_delay=2.0, max_delay=5.0)
        self.venues = venues or list(KNOWN_VENUES.keys())

    async def scrape_venue(self, slug: str) -> list[dict]:
        """Scrape all available shows from a venue's ShowGrounds page."""
        base_url = f"https://{slug}.showgroundslive.com"
        shows = []

        page = await self.new_page()
        try:
            # Navigate to the main browse page
            if not await self.navigate(page, f"{base_url}/browse/"):
                logger.warning("Cannot load %s", base_url)
                return shows

            # Find show/week selector (usually a dropdown or list)
            show_links = await self._find_show_links(page, base_url)
            logger.info("Found %d shows at %s", len(show_links), slug)

            for show_link in show_links:
                show_data = await self._scrape_show(page, show_link, slug)
                if show_data:
                    shows.append(show_data)
                await self.delay()

        finally:
            await page.close()

        return shows

    async def scrape_and_store(
        self,
        venues: list[str] | None = None,
        db_path: str | None = None,
    ):
        """Full pipeline: scrape venues, store in database."""
        init_db(db_path)
        session = get_session(db_path)
        target_venues = venues or self.venues

        try:
            for slug in target_venues:
                logger.info("Scraping venue: %s", slug)
                venue_info = KNOWN_VENUES.get(slug, {"name": slug, "country": "USA"})

                # Find or create venue
                venue = session.query(Venue).filter_by(showgrounds_slug=slug).first()
                if not venue:
                    venue = Venue(
                        name=venue_info["name"],
                        country=venue_info.get("country", "USA"),
                        state=venue_info.get("state"),
                        city=venue_info.get("city"),
                        showgrounds_slug=slug,
                    )
                    session.add(venue)
                    session.flush()

                shows = await self.scrape_venue(slug)

                for show_data in shows:
                    self._store_show(session, venue, show_data)

                session.commit()
                logger.info("Stored %d shows for %s", len(shows), slug)
                await self.delay()

        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _store_show(self, session, venue: Venue, show_data: dict):
        """Store a show and its FEI classes."""
        start = show_data.get("start_date", date.today())

        show = Show(
            venue_id=venue.id,
            name=show_data.get("name", venue.name),
            year=start.year,
            week_number=start.isocalendar()[1],
            start_date=start,
            end_date=show_data.get("end_date", start),
            star_level=show_data.get("star_level"),
            showgrounds_show_id=show_data.get("show_id"),
            source="showgrounds",
        )
        session.add(show)
        session.flush()

        for cls in show_data.get("classes", []):
            comp_class = CompetitionClass(
                show_id=show.id,
                name=cls.get("name", "Unknown"),
                class_number=cls.get("number"),
                fei_class_type=cls.get("type"),
                height_cm=cls.get("height_cm"),
                is_ranking_class=cls.get("is_ranking", False),
                entry_count=cls.get("entry_count"),
                starter_count=cls.get("starter_count"),
                prize_money=cls.get("prize_money"),
            )
            session.add(comp_class)

    async def _find_show_links(self, page: Page, base_url: str) -> list[dict]:
        """Find links to individual shows/weeks on the venue page."""
        links = []

        # Look for show selectors - typically a dropdown or sidebar with show weeks
        show_selector = page.locator(
            "select.show-selector, "
            "#showSelect, "
            "select[name*='show'], "
            ".show-list a, "
            ".week-selector a"
        )

        if await show_selector.count() > 0:
            tag = await show_selector.first.evaluate("el => el.tagName")

            if tag.lower() == "select":
                options = show_selector.first.locator("option")
                for i in range(await options.count()):
                    opt = options.nth(i)
                    value = await opt.get_attribute("value")
                    text = (await opt.inner_text()).strip()
                    if value and text:
                        links.append({
                            "url": f"{base_url}/browse/?show_id={value}",
                            "name": text,
                            "show_id": value,
                        })
            else:
                anchors = show_selector if tag.lower() == "a" else show_selector.locator("a")
                for i in range(await anchors.count()):
                    a = anchors.nth(i)
                    href = await a.get_attribute("href")
                    text = (await a.inner_text()).strip()
                    if href and text:
                        full_url = href if href.startswith("http") else f"{base_url}{href}"
                        links.append({"url": full_url, "name": text})

        # Fallback: look for any links with show/week identifiers
        if not links:
            all_links = page.locator("a[href*='show'], a[href*='sid=']")
            for i in range(min(await all_links.count(), 50)):
                a = all_links.nth(i)
                href = await a.get_attribute("href")
                text = (await a.inner_text()).strip()
                if href and text and len(text) > 3:
                    full_url = href if href.startswith("http") else f"{base_url}{href}"
                    links.append({"url": full_url, "name": text})

        return links

    async def _scrape_show(self, page: Page, show_link: dict, venue_slug: str) -> dict | None:
        """Scrape a single show's classes and entry counts."""
        url = show_link.get("url", "")
        if not await self.navigate(page, url):
            return None

        show_data = {
            "name": show_link.get("name", ""),
            "show_id": show_link.get("show_id"),
        }

        # Parse dates from page content
        page_text = await page.inner_text("body")
        date_match = re.search(
            r"(\w+\s+\d{1,2})\s*[-–]\s*(\w+\s+\d{1,2}),?\s*(\d{4})",
            page_text,
        )
        if date_match:
            year = int(date_match.group(3))
            try:
                start_str = f"{date_match.group(1)} {year}"
                show_data["start_date"] = datetime.strptime(start_str, "%B %d %Y").date()
                end_str = f"{date_match.group(2)} {year}"
                show_data["end_date"] = datetime.strptime(end_str, "%B %d %Y").date()
            except ValueError:
                pass

        # Parse star level from show name or page text
        full_text = f"{show_data['name']} {page_text[:500]}"
        star_match = re.search(r"CSI\s*(\d)\*", full_text)
        if star_match:
            show_data["star_level"] = int(star_match.group(1))

        # Collect classes
        show_data["classes"] = await self._parse_classes(page)

        return show_data

    async def _parse_classes(self, page: Page) -> list[dict]:
        """Parse class listings and entry counts from a show page."""
        classes = []

        # Look for class/division tables
        rows = page.locator(
            "table.classes-table tr, "
            ".class-row, "
            ".division-row, "
            "table tr:has(td)"
        )
        count = await rows.count()

        for i in range(count):
            row = rows.nth(i)
            text = await row.inner_text()

            # Only interested in FEI classes
            if not _is_fei_class(text):
                continue

            cls_data: dict = {"name": text.split("\n")[0].strip()[:200]}

            # Extract entry count - look for "Entries: X" or just a number in entries column
            entry_match = re.search(r"(?:Entries|Ent)[:\s]*(\d+)", text, re.IGNORECASE)
            if entry_match:
                cls_data["entry_count"] = int(entry_match.group(1))
            else:
                # Try to find entry count in a specific column
                cells = row.locator("td")
                cell_count = await cells.count()
                for j in range(cell_count):
                    cell = cells.nth(j)
                    cell_text = (await cell.inner_text()).strip()
                    # Check if cell header or class suggests this is the entries column
                    if re.match(r"^\d{1,3}$", cell_text):
                        cls_data.setdefault("entry_count", int(cell_text))

            # Height
            height_match = re.search(r"(\d\.\d{2})m|(\d{3})cm", text)
            if height_match:
                if height_match.group(1):
                    cls_data["height_cm"] = int(float(height_match.group(1)) * 100)
                else:
                    cls_data["height_cm"] = int(height_match.group(2))

            # Prize money
            prize_match = re.search(r"\$[\d,]+", text)
            if prize_match:
                cls_data["prize_money"] = float(prize_match.group().replace("$", "").replace(",", ""))

            # Class type
            name = cls_data["name"]
            if "Grand Prix" in name:
                cls_data["type"] = "Grand Prix"
                cls_data["is_ranking"] = True
            elif re.search(r"World Cup", name, re.IGNORECASE):
                cls_data["type"] = "World Cup"
                cls_data["is_ranking"] = True
            elif re.search(r"Ranking", name, re.IGNORECASE):
                cls_data["type"] = "Ranking"
                cls_data["is_ranking"] = True
            else:
                cls_data["type"] = "Jumping"
                cls_data["is_ranking"] = False

            # Class number
            num_match = re.search(r"(?:Class|#)\s*(\d+)", text, re.IGNORECASE)
            if num_match:
                cls_data["number"] = num_match.group(1)

            classes.append(cls_data)

        return classes
