import asyncio
import logging
import random

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

logger = logging.getLogger(__name__)


class BaseScraper:
    """Base scraper with Playwright browser automation, rate limiting, and retry logic."""

    def __init__(self, headless: bool = True, min_delay: float = 2.0, max_delay: float = 5.0):
        self.headless = headless
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def start(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
        )
        logger.info("Browser started (headless=%s)", self.headless)

    async def stop(self):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser stopped")

    async def new_page(self) -> Page:
        if not self._context:
            raise RuntimeError("Call start() before creating pages")
        return await self._context.new_page()

    async def delay(self):
        wait = random.uniform(self.min_delay, self.max_delay)
        logger.debug("Waiting %.1fs", wait)
        await asyncio.sleep(wait)

    async def navigate(self, page: Page, url: str, retries: int = 3) -> bool:
        for attempt in range(1, retries + 1):
            try:
                response = await page.goto(url, wait_until="networkidle", timeout=30000)
                if response and response.ok:
                    logger.info("Loaded %s", url)
                    return True
                logger.warning("Got status %s for %s (attempt %d)", response.status if response else "None", url, attempt)
            except Exception as e:
                logger.warning("Error loading %s (attempt %d): %s", url, attempt, e)
            if attempt < retries:
                backoff = 2 ** attempt
                await asyncio.sleep(backoff)
        logger.error("Failed to load %s after %d attempts", url, retries)
        return False

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.stop()
