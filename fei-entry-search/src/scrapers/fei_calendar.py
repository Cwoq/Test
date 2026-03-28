import logging
import re
from datetime import date, datetime

from playwright.async_api import Page

from src.db.database import get_session, init_db
from src.db.models import CompetitionClass, Show, Venue

from .base import BaseScraper

logger = logging.getLogger(__name__)

CALENDAR_URL = "https://data.fei.org/Calendar/Search.aspx"
EVENT_DETAIL_URL = "https://data.fei.org/Calendar/EventDetail.aspx"

# North American national federation codes
NA_FEDERATIONS = ["USA", "CAN", "MEX"]

# Patterns that identify FEI ranking classes in jumping
RANKING_CLASS_PATTERNS = [
    r"Grand Prix",
    r"Ranking",
    r"CSI.*Table\s*A",
    r"FEI.*Jumping",
    r"World Cup",
    r"Nations Cup",
    r"LONGINES",
]


def is_ranking_class(class_name: str) -> bool:
    for pattern in RANKING_CLASS_PATTERNS:
        if re.search(pattern, class_name, re.IGNORECASE):
            return True
    return False


def parse_star_level(text: str) -> int | None:
    match = re.search(r"CSI\s*(\d)\*", text)
    if match:
        return int(match.group(1))
    # Also handle written forms like "CSI5*-W"
    match = re.search(r"CSI(\d)", text)
    if match:
        return int(match.group(1))
    return None


def parse_height_cm(text: str) -> int | None:
    match = re.search(r"(\d{3})\s*cm", text)
    if match:
        return int(match.group(1))
    # Try common heights like 1.45m, 1.50m
    match = re.search(r"(\d\.\d{2})\s*m", text)
    if match:
        return int(float(match.group(1)) * 100)
    return None


class FEICalendarScraper(BaseScraper):
    """Scrapes FEI data.fei.org for jumping competition calendar and results."""

    def __init__(self, headless: bool = True):
        super().__init__(headless=headless, min_delay=2.0, max_delay=4.0)

    async def scrape_calendar(
        self,
        start_date: date,
        end_date: date,
        federations: list[str] | None = None,
    ) -> list[dict]:
        """Scrape the FEI calendar for jumping events in North America."""
        federations = federations or NA_FEDERATIONS
        events = []

        page = await self.new_page()
        try:
            if not await self.navigate(page, CALENDAR_URL):
                logger.error("Cannot load FEI calendar search page")
                return events

            # Set discipline to Jumping
            await self._select_discipline(page, "Jumping")
            await self.delay()

            for nf in federations:
                logger.info("Searching events for NF=%s from %s to %s", nf, start_date, end_date)

                await self._set_national_federation(page, nf)
                await self._set_date_range(page, start_date, end_date)
                await self._click_search(page)
                await self.delay()

                nf_events = await self._collect_event_links(page)
                logger.info("Found %d events for %s", len(nf_events), nf)
                events.extend(nf_events)

        finally:
            await page.close()

        return events

    async def scrape_event_details(self, event_url: str) -> dict | None:
        """Scrape a single event's details and class results."""
        page = await self.new_page()
        try:
            if not await self.navigate(page, event_url):
                return None

            details = await self._parse_event_page(page)
            await self.delay()

            # Navigate to results tab if available
            results_tab = page.locator("a:has-text('Results'), a:has-text('Comp.')")
            if await results_tab.count() > 0:
                await results_tab.first.click()
                await page.wait_for_load_state("networkidle")
                await self.delay()
                details["classes"] = await self._parse_results_page(page)
            else:
                details["classes"] = []

            return details
        finally:
            await page.close()

    async def scrape_and_store(
        self,
        start_date: date,
        end_date: date,
        db_path: str | None = None,
    ):
        """Full pipeline: scrape events, get details, store in database."""
        init_db(db_path)
        session = get_session(db_path)

        try:
            events = await self.scrape_calendar(start_date, end_date)

            for event_info in events:
                event_url = event_info.get("url")
                if not event_url:
                    continue

                logger.info("Scraping event: %s", event_info.get("name", event_url))
                details = await self.scrape_event_details(event_url)
                if not details:
                    continue

                self._store_event(session, details)
                await self.delay()

            session.commit()
            logger.info("Stored %d events in database", len(events))
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _store_event(self, session, details: dict):
        """Store an event and its classes in the database."""
        venue_name = details.get("venue", "Unknown Venue")
        country = details.get("country", "USA")

        # Find or create venue
        venue = session.query(Venue).filter_by(name=venue_name, country=country).first()
        if not venue:
            venue = Venue(
                name=venue_name,
                country=country,
                city=details.get("city"),
                state=details.get("state"),
                fei_venue_id=details.get("fei_venue_id"),
            )
            session.add(venue)
            session.flush()

        start = details.get("start_date", date.today())
        show = Show(
            venue_id=venue.id,
            name=details.get("name", venue_name),
            year=start.year,
            week_number=start.isocalendar()[1],
            start_date=start,
            end_date=details.get("end_date", start),
            star_level=details.get("star_level"),
            fei_event_id=details.get("fei_event_id"),
            source="fei",
        )
        session.add(show)
        session.flush()

        for cls_data in details.get("classes", []):
            comp_class = CompetitionClass(
                show_id=show.id,
                name=cls_data.get("name", "Unknown"),
                class_number=cls_data.get("number"),
                fei_class_type=cls_data.get("type"),
                height_cm=cls_data.get("height_cm"),
                is_ranking_class=cls_data.get("is_ranking", False),
                entry_count=cls_data.get("entry_count"),
                starter_count=cls_data.get("starter_count"),
                prize_money=cls_data.get("prize_money"),
            )
            session.add(comp_class)

    async def _select_discipline(self, page: Page, discipline: str):
        """Select a discipline from the search form."""
        selector = page.locator("#ContentPlaceHolder1_ddlDiscipline, select[name*='Discipline']")
        if await selector.count() > 0:
            await selector.select_option(label=discipline)
        else:
            # Try clicking a discipline link/button
            disc_link = page.locator(f"text={discipline}").first
            if await disc_link.count() > 0:
                await disc_link.click()

    async def _set_national_federation(self, page: Page, nf_code: str):
        """Set the National Federation filter."""
        selector = page.locator(
            "#ContentPlaceHolder1_ddlNF, "
            "select[name*='NationalFederation'], "
            "select[name*='NF']"
        )
        if await selector.count() > 0:
            await selector.select_option(value=nf_code)

    async def _set_date_range(self, page: Page, start: date, end: date):
        """Set the date range in the search form."""
        start_input = page.locator(
            "#ContentPlaceHolder1_txtDateFrom, input[name*='DateFrom'], input[name*='startDate']"
        )
        end_input = page.locator(
            "#ContentPlaceHolder1_txtDateTo, input[name*='DateTo'], input[name*='endDate']"
        )

        if await start_input.count() > 0:
            await start_input.fill(start.strftime("%d/%m/%Y"))
        if await end_input.count() > 0:
            await end_input.fill(end.strftime("%d/%m/%Y"))

    async def _click_search(self, page: Page):
        """Click the search button."""
        btn = page.locator(
            "#ContentPlaceHolder1_btnSearch, "
            "input[type='submit'][value='Search'], "
            "button:has-text('Search')"
        )
        if await btn.count() > 0:
            await btn.first.click()
            await page.wait_for_load_state("networkidle")

    async def _collect_event_links(self, page: Page) -> list[dict]:
        """Collect event links from search results, paginating if needed."""
        all_events = []

        while True:
            rows = page.locator("table.rgMasterTable tr, table.GridView tr, #results-table tr")
            count = await rows.count()

            for i in range(count):
                row = rows.nth(i)
                link = row.locator("a[href*='EventDetail']").first
                if await link.count() == 0:
                    continue

                href = await link.get_attribute("href")
                text = await row.inner_text()

                event = {
                    "url": href if href.startswith("http") else f"https://data.fei.org{href}",
                    "name": (await link.inner_text()).strip(),
                    "raw_text": text.strip(),
                    "star_level": parse_star_level(text),
                }
                all_events.append(event)

            # Check for next page
            next_btn = page.locator("a:has-text('Next'), a.rgPageNext, .next-page a")
            if await next_btn.count() > 0 and await next_btn.first.is_enabled():
                await next_btn.first.click()
                await page.wait_for_load_state("networkidle")
                await self.delay()
            else:
                break

        return all_events

    async def _parse_event_page(self, page: Page) -> dict:
        """Parse event detail page for show info."""
        details: dict = {}

        # Event name
        title = page.locator("h1, h2, .event-title, #ContentPlaceHolder1_lblEventName")
        if await title.count() > 0:
            details["name"] = (await title.first.inner_text()).strip()

        # Try to extract structured info from the page
        page_text = await page.inner_text("body")

        details["star_level"] = parse_star_level(page_text)

        # Parse dates - look for patterns like "01/01/2025 - 05/01/2025"
        date_match = re.search(r"(\d{2}/\d{2}/\d{4})\s*[-–]\s*(\d{2}/\d{2}/\d{4})", page_text)
        if date_match:
            try:
                details["start_date"] = datetime.strptime(date_match.group(1), "%d/%m/%Y").date()
                details["end_date"] = datetime.strptime(date_match.group(2), "%d/%m/%Y").date()
            except ValueError:
                pass

        # Venue / location info
        venue_el = page.locator(".venue-name, #ContentPlaceHolder1_lblVenue, td:has-text('Venue') + td")
        if await venue_el.count() > 0:
            details["venue"] = (await venue_el.first.inner_text()).strip()

        # Country
        country_el = page.locator("#ContentPlaceHolder1_lblNF, td:has-text('NF') + td")
        if await country_el.count() > 0:
            details["country"] = (await country_el.first.inner_text()).strip()[:3].upper()

        # FEI Event ID
        fei_id_match = re.search(r"FEI\s*(?:Event\s*)?(?:ID|Code)[:\s]*(\w+)", page_text, re.IGNORECASE)
        if fei_id_match:
            details["fei_event_id"] = fei_id_match.group(1)

        return details

    async def _parse_results_page(self, page: Page) -> list[dict]:
        """Parse results/competition page for class entry counts."""
        classes = []

        rows = page.locator(
            "table tr:has(td), "
            ".competition-row, "
            ".comp-list-item"
        )
        count = await rows.count()

        for i in range(count):
            row = rows.nth(i)
            text = await row.inner_text()

            if not any(kw in text.upper() for kw in ["JUMPING", "CSI", "GRAND PRIX", "TABLE A", "TABLE C"]):
                continue

            cells = row.locator("td")
            cell_count = await cells.count()

            cls_data: dict = {"name": text.split("\n")[0].strip() if text else "Unknown"}

            # Try to extract entry/starter count from cells
            for j in range(cell_count):
                cell_text = (await cells.nth(j).inner_text()).strip()

                # Look for numbers that could be entry counts
                if re.match(r"^\d{1,3}$", cell_text):
                    num = int(cell_text)
                    if "entry_count" not in cls_data and 1 <= num <= 200:
                        cls_data["entry_count"] = num
                    elif "starter_count" not in cls_data and 1 <= num <= 200:
                        cls_data["starter_count"] = num

            cls_data["height_cm"] = parse_height_cm(text)
            cls_data["is_ranking"] = is_ranking_class(text)

            # Extract class type
            if "Grand Prix" in text:
                cls_data["type"] = "Grand Prix"
            elif "World Cup" in text.upper() or "WC" in text.upper():
                cls_data["type"] = "World Cup"
            elif "Nations Cup" in text:
                cls_data["type"] = "Nations Cup"
            elif re.search(r"Table\s*A", text, re.IGNORECASE):
                cls_data["type"] = "Table A"
            elif re.search(r"Table\s*C", text, re.IGNORECASE):
                cls_data["type"] = "Speed (Table C)"
            else:
                cls_data["type"] = "Jumping"

            classes.append(cls_data)

        return classes
