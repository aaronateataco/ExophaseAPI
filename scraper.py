import re
import logging
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup, Tag

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("exophase_scraper")

# Custom Exceptions for clean API responses
class ScraperError(Exception):
    """Base exception for Exophase Scraper."""
    pass

class UserNotFoundError(ScraperError):
    """Raised when the Exophase user profile does not exist (404)."""
    pass

class PrivateProfileError(ScraperError):
    """Raised when the user's profile is private (403)."""
    pass

class NotSupportedError(ScraperError):
    """Raised when the requested data requires JS rendering and cannot be scraped."""
    pass


# Platform normalisation table: data-environment value -> display name
_PLATFORM_ENV_MAP = {
    "steam":     "Steam",
    "psn":       "PSN",
    "xbox":      "Xbox",
    "retro":     "RetroAchievements",
    "android":   "Google Play",
    "gog":       "GOG",
    "epic":      "Epic Games",
    "nintendo":  "Nintendo",
    "apple":     "Apple Game Center",
    "uplay":     "Ubisoft",
    "blizzard":  "Blizzard",
    "stadia":    "Stadia",
    "origin":    "Electronic Arts",
}


class ExophaseScraper:
    """
    A BeautifulSoup4 + HTTPX scraper for Exophase.com public profile pages.

    Notes
    -----
    * The games list is loaded entirely via a Cloudflare-protected JSON API
      and a Vue.js SPA — it is not available in static HTML and cannot be
      reached by a plain HTTP client.  The `scrape_games` method raises
      `NotSupportedError` with a descriptive message.
    * Profile data IS present in the server-rendered HTML and is fully
      supported.
    """

    def __init__(self, timeout: float = 15.0):
        self.base_url = "https://www.exophase.com"
        # Modern browser headers to avoid trivial bot-detection blocks
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.exophase.com/",
        }
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_html(self, client: httpx.AsyncClient, url: str) -> str:
        """Fetch HTML content, translating HTTP errors to typed exceptions."""
        try:
            response = await client.get(
                url, headers=self.headers, timeout=self.timeout,
                follow_redirects=True,
            )
            if response.status_code == 404:
                raise UserNotFoundError(f"Profile not found at: {url}")
            if response.status_code == 403:
                raise PrivateProfileError(f"Access forbidden at: {url}")
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise UserNotFoundError(f"Profile not found at: {url}")
            elif e.response.status_code == 403:
                raise PrivateProfileError(f"Access forbidden at: {url}")
            raise ScraperError(f"HTTP error: {e}")
        except httpx.RequestError as e:
            raise ScraperError(f"Network request failed: {e}")

    @staticmethod
    def _extract_first_number(text: str) -> str:
        """Return the first integer-or-decimal token found in *text*, or '0'."""
        m = re.search(r'[\d,]+(?:\.\d+)?', text)
        if not m:
            return "0"
        return m.group(0).replace(",", "")

    @staticmethod
    def _parse_float(text: str) -> float:
        try:
            return round(float(ExophaseScraper._extract_first_number(text)), 2)
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_int(text: str) -> int:
        try:
            return int(ExophaseScraper._extract_first_number(text))
        except ValueError:
            return 0

    @staticmethod
    def _parse_percentage(text: str) -> float:
        """Extract a percentage value like '15.38%' → 15.38."""
        m = re.search(r'([\d.]+)\s*%', text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
        return ExophaseScraper._parse_float(text)

    @staticmethod
    def _direct_text(tag: Tag) -> str:
        """
        Return only the direct (non-nested) text nodes of *tag*, joined.
        Useful for elements like <span>icon<i/>  4,385 <span>hours</span></span>
        where we only want '4,385'.
        """
        return " ".join(
            str(child).strip()
            for child in tag.children
            if isinstance(child, str) and child.strip()
        )

    # ------------------------------------------------------------------
    # Public scraping methods
    # ------------------------------------------------------------------

    async def scrape_profile(self, username: str) -> Dict[str, Any]:
        """
        Scrape Exophase user profile details from the server-rendered HTML.

        Endpoint: GET /api/v1/user/{username}/profile
        """
        url = f"{self.base_url}/user/{username}/"

        async with httpx.AsyncClient() as client:
            html = await self._get_html(client, url)

        soup = BeautifulSoup(html, "html.parser")

        # ── 1. Avatar URL ──────────────────────────────────────────────
        pfp_url: Optional[str] = None
        avatar_img = soup.select_one(".avatar img, .avatar.rounded img")
        if avatar_img:
            pfp_url = avatar_img.get("src")
        if pfp_url and pfp_url.startswith("/"):
            pfp_url = self.base_url + pfp_url

        # ── 2. Completion percentage ───────────────────────────────────
        # <span class="percentage-label">15.38%</span>
        completion_percentage = 0.0
        pct_el = soup.select_one(".percentage-label")
        if pct_el:
            completion_percentage = self._parse_percentage(pct_el.get_text())

        # ── 3. Playtime ────────────────────────────────────────────────
        # <span class="tippy playtime" ...> <i/> 4,385 <span>hours</span> </span>
        total_playtime_hours = 0.0
        playtime_el = soup.select_one("span.playtime")
        if playtime_el:
            raw = self._direct_text(playtime_el)
            total_playtime_hours = self._parse_float(raw)

        # ── 4. Total achievements / trophies ───────────────────────────
        # <span class="tippy total-value" ...> <i/> 731 </span>
        total_achievements = 0
        awards_el = soup.select_one("span.total-value")
        if awards_el:
            raw = self._direct_text(awards_el)
            total_achievements = self._parse_int(raw)

        # ── 5. Connected platforms ─────────────────────────────────────
        # <ul id="award-overview">
        #   <li class="... steam service-widget" data-environment="steam">
        #     <div class="service-stats">
        #       <span class="big">231</span>
        #       <span class="sub">Steam</span>
        #     </div>
        #   </li>
        # </ul>
        platforms: List[str] = []
        for widget in soup.select("li.service-widget[data-environment]"):
            env = widget.get("data-environment", "").lower()
            display = _PLATFORM_ENV_MAP.get(env)
            if display is None:
                # Fall back to the text inside span.sub
                sub_el = widget.select_one("span.sub")
                display = sub_el.get_text().strip() if sub_el else env.capitalize()
            if display:
                platforms.append(display)

        return {
            "username": username,
            "profile_picture_url": pfp_url,
            "stats": {
                "total_achievements": total_achievements,
                "total_playtime_hours": total_playtime_hours,
                "overall_completion_percentage": completion_percentage,
            },
            "connected_platforms": platforms,
            "profile_url": url,
        }

    async def scrape_games(self, username: str) -> List[Dict[str, Any]]:
        """
        NOT SUPPORTED — Exophase's game list is served exclusively through a
        Cloudflare-protected JSON API consumed by a Vue.js SPA.  A plain HTTP
        scraper cannot pass the JS challenge and therefore cannot retrieve game
        data.

        Raises
        ------
        NotSupportedError
            Always, with a descriptive message.
        """
        raise NotSupportedError(
            "The Exophase games list is loaded dynamically via a Cloudflare-protected "
            "API endpoint (api.exophase.com) that requires JavaScript execution to "
            "access.  A server-side HTML scraper cannot retrieve this data without a "
            "headless browser (e.g. Playwright or Selenium).  Profile data is still "
            "fully available via GET /api/v1/user/{username}/profile."
        )
