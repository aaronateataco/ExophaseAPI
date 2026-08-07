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

class ExophaseScraper:
    """
    A robust BeautifulSoup4 and HTTPX based scraper for Exophase.com.
    Uses resilient, multi-tiered selector matching and regular expressions
    to survive potential target HTML structure changes.
    """
    def __init__(self, timeout: float = 10.0):
        self.base_url = "https://www.exophase.com"
        # Modern headers to emulate a standard web browser and prevent access blocks
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.exophase.com/",
        }
        self.timeout = timeout

    async def _get_html(self, client: httpx.AsyncClient, url: str) -> str:
        """Helper to fetch HTML content with exception translation."""
        try:
            response = await client.get(url, headers=self.headers, timeout=self.timeout, follow_redirects=True)
            if response.status_code == 404:
                raise UserNotFoundError(f"User profile or page not found at: {url}")
            if response.status_code == 403:
                raise PrivateProfileError(f"Access forbidden or profile is private at: {url}")
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise UserNotFoundError(f"User profile or page not found at: {url}")
            elif e.response.status_code == 403:
                raise PrivateProfileError(f"Access forbidden or profile is private at: {url}")
            raise ScraperError(f"HTTP error occurred: {e}")
        except httpx.RequestError as e:
            raise ScraperError(f"Network request failed: {e}")

    def _clean_numeric_string(self, text: str) -> str:
        """Cleans formatting (commas, spaces, symbols) from numbers."""
        cleaned = re.sub(r'[^\d.]', '', text)
        return cleaned if cleaned else "0"

    def _parse_completion_rate(self, text: str) -> float:
        """Parses completion percentage from string (e.g. '75.4%', '75 %' -> 75.4)."""
        try:
            match = re.search(r'([\d.]+)\s*%', text)
            if match:
                return float(match.group(1))
            cleaned = self._clean_numeric_string(text)
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0

    def _parse_playtime(self, text: str) -> float:
        """
        Parses playtime string into hours.
        Supports formats: '1,234 hours', '45.5h', '30m' -> 0.5h, etc.
        """
        text_lower = text.lower().strip()
        try:
            if 'm' in text_lower and 'h' not in text_lower:
                # Minutes format (e.g., "45m" or "45 mins")
                mins = float(self._clean_numeric_string(text_lower))
                return round(mins / 60.0, 2)
            # Hours format
            hours = float(self._clean_numeric_string(text_lower))
            return round(hours, 2)
        except ValueError:
            return 0.0

    async def scrape_profile(self, username: str) -> Dict[str, Any]:
        """
        Scrapes Exophase user profile details.
        Endpoint: GET /api/v1/user/{username}/profile
        """
        url = f"{self.base_url}/user/{username}/"
        
        async with httpx.AsyncClient() as client:
            html = await self._get_html(client, url)
            
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. PFP URL extraction with fallback
        pfp_url = None
        # Try primary avatar container
        pfp_container = soup.select_one(".user-avatar img, .avatar img, .player-avatar img")
        if pfp_container and pfp_container.get("src"):
            pfp_url = pfp_container["src"]
        else:
            # Fallback: scan all images for avatar indicators
            for img in soup.find_all("img"):
                src = img.get("src", "")
                alt = img.get("alt", "").lower()
                if "avatar" in src or "avatar" in alt or username.lower() in alt:
                    pfp_url = src
                    break
        
        # Ensure absolute URL
        if pfp_url and pfp_url.startswith("/"):
            pfp_url = self.base_url + pfp_url

        # 2. Parse Profile Stats (Achievements, Playtime, Completion)
        # Exophase uses a statistic list in user headers
        total_achievements = 0
        total_playtime_hours = 0.0
        completion_percentage = 0.0
        
        # Method A: Parse via metadata divs (Exophase standard layout)
        # Class names often include 'stat-achievements', 'stat-playtime', 'stat-completion'
        stat_blocks = soup.select(".user-stats .stat, .player-stats .stat, .profile-stats .stat")
        if stat_blocks:
            for block in stat_blocks:
                label_el = block.select_one(".label, .title, span")
                val_el = block.select_one(".value, .num, strong")
                if label_el and val_el:
                    label = label_el.text.strip().lower()
                    val_text = val_el.text.strip()
                    if "achievement" in label:
                        total_achievements = int(self._clean_numeric_string(val_text))
                    elif "playtime" in label or "hours" in label:
                        total_playtime_hours = self._parse_playtime(val_text)
                    elif "completion" in label or "%" in label:
                        completion_percentage = self._parse_completion_rate(val_text)
                        
        # Method B Fallback: Scan text labels anywhere on page if specific blocks are not found
        if total_achievements == 0:
            for label_text in ["achievements", "playtime", "completion", "completed"]:
                elements = soup.find_all(text=re.compile(rf"\b{label_text}\b", re.IGNORECASE))
                for el in elements:
                    # Look at parent elements for numbers
                    parent = el.parent
                    if not parent:
                        continue
                    combined_text = parent.get_text()
                    numbers = re.findall(r'[\d,.]+', combined_text)
                    if numbers:
                        # Find the first valid number or percentage
                        if "achievement" in label_text:
                            total_achievements = int(self._clean_numeric_string(numbers[0]))
                        elif "playtime" in label_text:
                            total_playtime_hours = self._parse_playtime(combined_text)
                        elif "completion" in label_text or "completed" in label_text:
                            if "%" in combined_text:
                                completion_percentage = self._parse_completion_rate(combined_text)

        # 3. Detect Connected Platforms
        # Check active platform tabs, badges, or platform links
        platforms = set()
        
        # Try to find platform links (Steam, Xbox, PSN, RetroAchievements, etc.)
        # Exophase profile sidebar/header usually contains list of connected profiles
        profile_links = soup.select(".profile-links a, .connected-accounts a, .user-socials a")
        for link in profile_links:
            href = link.get("href", "").lower()
            class_list = " ".join(link.get("class", [])).lower()
            
            if "steam" in href or "steam" in class_list:
                platforms.add("Steam")
            elif "xbox" in href or "live.xbox" in href or "xbox" in class_list:
                platforms.add("Xbox")
            elif "playstation" in href or "psn" in href or "sony" in href or "psn" in class_list:
                platforms.add("PSN")
            elif "retroachievements" in href or "ra" in class_list:
                platforms.add("RetroAchievements")
            elif "gog" in href or "gog" in class_list:
                platforms.add("GOG")
            elif "epic" in href or "epic" in class_list:
                platforms.add("Epic Games")
            elif "switch" in href or "nintendo" in href:
                platforms.add("Nintendo Switch")

        # Fallback for platforms: scan platform icon badges
        platform_badges = soup.select(".platform-icon, .badge-platform, .user-platforms span")
        for badge in platform_badges:
            classes = " ".join(badge.get("class", [])).lower()
            text = badge.text.strip().lower()
            for plat_candidate, display_name in [
                ("steam", "Steam"),
                ("xbox", "Xbox"),
                ("psn", "PSN"),
                ("playstation", "PSN"),
                ("retro", "RetroAchievements"),
                ("ra-", "RetroAchievements"),
                ("gog", "GOG"),
                ("epic", "Epic Games"),
                ("switch", "Nintendo Switch"),
                ("nintendo", "Nintendo Switch"),
            ]:
                if plat_candidate in classes or plat_candidate in text:
                    platforms.add(display_name)

        return {
            "username": username,
            "profile_picture_url": pfp_url,
            "stats": {
                "total_achievements": total_achievements,
                "total_playtime_hours": total_playtime_hours,
                "overall_completion_percentage": completion_percentage,
            },
            "connected_platforms": sorted(list(platforms)),
            "profile_url": url,
        }

    async def scrape_games(self, username: str) -> List[Dict[str, Any]]:
        """
        Scrapes the user's games list.
        Endpoint: GET /api/v1/user/{username}/games
        """
        url = f"{self.base_url}/user/{username}/games/"
        
        async with httpx.AsyncClient() as client:
            html = await self._get_html(client, url)
            
        soup = BeautifulSoup(html, "html.parser")
        games_list = []
        
        # Exophase games are listed in a table or list rows.
        # Primary container: .games-list or a table with rows having .game or class 'game-row'
        game_rows = soup.select(".games-list tr, table.games tr, .game-list-row, .game-row, tr.game")
        
        # If rows are empty, try generic table rows excluding headers
        if not game_rows:
            game_rows = [tr for tr in soup.select("table tr") if tr.select_one("a[href*='/game/']")]

        for row in game_rows:
            # Skip header row if it exists
            if row.find("th") or "header" in "".join(row.get("class", [])).lower():
                continue
                
            # Find game title and link
            title_el = row.select_one(".title a, a[href*='/game/'], .game-title a")
            if not title_el:
                continue
                
            game_title = title_el.text.strip()
            relative_game_url = title_el["href"]
            full_game_url = self.base_url + relative_game_url if relative_game_url.startswith("/") else relative_game_url
            
            # Extract Game ID/slug from URL (e.g., https://www.exophase.com/game/destiny-2-psn/ -> destiny-2-psn)
            game_slug = relative_game_url.strip("/").split("/")[-1]
            
            # Detect platform
            # Often indicated by class names (e.g. 'steam', 'psn') or an icon/span text
            platform = "Unknown"
            platform_el = row.select_one(".platform, .platform-icon, .type, td.plat")
            if platform_el:
                platform_text = platform_el.text.strip()
                if platform_text:
                    platform = platform_text
                else:
                    # Check classes if text is empty (icon only)
                    classes = " ".join(platform_el.get("class", [])).lower()
                    for plat_key, display_name in [
                        ("steam", "Steam"),
                        ("xbox", "Xbox"),
                        ("psn", "PSN"),
                        ("playstation", "PSN"),
                        ("retro", "RetroAchievements"),
                        ("gog", "GOG"),
                        ("epic", "Epic Games"),
                    ]:
                        if plat_key in classes:
                            platform = display_name
                            break
            
            if platform == "Unknown":
                # Fallback: scan URL or classes of the row itself
                row_classes = " ".join(row.get("class", [])).lower()
                for plat_key, display_name in [
                    ("steam", "Steam"),
                    ("xbox", "Xbox"),
                    ("psn", "PSN"),
                    ("retro", "RetroAchievements"),
                    ("gog", "GOG"),
                    ("epic", "Epic Games"),
                ]:
                    if plat_key in row_classes or plat_key in game_slug:
                        platform = display_name
                        break
                        
            # Completion Percentage
            completion_percentage = 0.0
            completion_el = row.select_one(".percent, .completion, .completed, td.pct")
            if completion_el:
                completion_percentage = self._parse_completion_rate(completion_el.text)
            else:
                # Fallback: Search row cells for percentage format
                for cell in row.find_all(["td", "div"]):
                    cell_text = cell.text.strip()
                    if "%" in cell_text:
                        completion_percentage = self._parse_completion_rate(cell_text)
                        break

            # Playtime
            playtime_hours = 0.0
            playtime_el = row.select_one(".hours, .playtime, .time, td.hours-played")
            if playtime_el:
                playtime_hours = self._parse_playtime(playtime_el.text)
            else:
                # Fallback: scan for playtime elements using regular expressions
                for cell in row.find_all(["td", "div"]):
                    cell_text = cell.text.strip().lower()
                    if "hour" in cell_text or "h" in cell_text or "min" in cell_text:
                        playtime_hours = self._parse_playtime(cell_text)
                        break
                        
            games_list.append({
                "game_title": game_title,
                "platform": platform,
                "completion_percentage": completion_percentage,
                "playtime_hours": playtime_hours,
                "game_slug": game_slug,
                "game_url": full_game_url
            })
            
        return games_list
