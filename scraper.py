import re
import asyncio
import logging
from datetime import datetime, timezone
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
      reached by a plain HTTP client.  It IS reachable via the private
      `api.exophase.com` JSON API the site's own Vue frontend calls
      (`GET /public/player/{playerid}/games`, `/awards`, and
      `/game/{master_id}/earned`) — no headless browser needed, just the
      right endpoint and headers.  `scrape_games` and
      `scrape_user_game_achievements` use it.
    * Profile data IS present in the server-rendered HTML and is fully
      supported.
    """

    def __init__(self, timeout: float = 15.0):
        self.base_url = "https://www.exophase.com"
        self.api_base_url = "https://api.exophase.com"
        self.media_base_url = "https://m.exophase.com"
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
        # The JSON API rejects requests that don't look like the site's own
        # XHR calls.
        self.api_headers = {
            **self.headers,
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
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

    async def _get_json(
        self, client: httpx.AsyncClient, url: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Fetch from the private api.exophase.com JSON API."""
        try:
            response = await client.get(
                url, headers=self.api_headers, params=params,
                timeout=self.timeout, follow_redirects=True,
            )
            if response.status_code == 404:
                raise UserNotFoundError(f"Not found at: {url}")
            if response.status_code == 403:
                raise PrivateProfileError(f"Access forbidden at: {url}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise UserNotFoundError(f"Not found at: {url}")
            elif e.response.status_code == 403:
                raise PrivateProfileError(f"Access forbidden at: {url}")
            raise ScraperError(f"HTTP error: {e}")
        except httpx.RequestError as e:
            raise ScraperError(f"Network request failed: {e}")

    @staticmethod
    def _slug_from_endpoint(endpoint_url: Optional[str]) -> Optional[str]:
        """Pull the game slug out of an endpoint_awards URL like
        'https://www.exophase.com/game/brotato-steam/achievements/#123'."""
        if not endpoint_url:
            return None
        m = re.search(r"/game/([^/]+)/achievements", endpoint_url)
        return m.group(1) if m else None

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

        soup = BeautifulSoup(html, "lxml")

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

        # ── 6. Per-platform breakdown ──────────────────────────────────
        # Each linked platform gets its own
        # <section class="row align-items-center {env}"> block (the first
        # such section, class "...global", is the aggregate already parsed
        # above), carrying that platform's own username, completion %,
        # playtime, achievements earned, games owned and global rank.
        platform_stats: List[Dict[str, Any]] = []
        for section in soup.select("section.row.align-items-center"):
            classes = section.get("class") or []
            env = next((c for c in classes if c not in ("row", "align-items-center")), None)
            if not env or env == "global":
                continue

            display = _PLATFORM_ENV_MAP.get(env, env.capitalize())

            username_el = section.select_one(".column-username h2")
            platform_username = username_el.get_text(strip=True) if username_el else None

            pct_el = section.select_one(".percentage-label")
            platform_completion = self._parse_percentage(pct_el.get_text()) if pct_el else 0.0

            playtime_el = section.select_one("span.playtime")
            platform_playtime = self._parse_float(self._direct_text(playtime_el)) if playtime_el else 0.0

            total_el = section.select_one(
                'span.total-value[data-tippy-content="Total Trophies and Achievements Earned"]'
            )
            platform_achievements = self._parse_int(self._direct_text(total_el)) if total_el else 0

            games_el = section.select_one('span[data-tippy-content="Games Owned"]')
            games_owned = self._parse_int(self._direct_text(games_el)) if games_el else 0

            rank_el = section.select_one(".global-ranking")
            global_rank = self._parse_int(rank_el.get_text()) if rank_el else None

            platform_stats.append({
                "platform": display,
                "platform_username": platform_username,
                "completion_percentage": platform_completion,
                "playtime_hours": platform_playtime,
                "achievements_earned": platform_achievements,
                "games_owned": games_owned,
                "global_rank": global_rank,
            })

        return {
            "username": username,
            "profile_picture_url": pfp_url,
            "stats": {
                "total_achievements": total_achievements,
                "total_playtime_hours": total_playtime_hours,
                "overall_completion_percentage": completion_percentage,
            },
            "connected_platforms": platforms,
            "platforms": platform_stats,
            "profile_url": url,
        }

    async def _resolve_master_playerid(self, client: httpx.AsyncClient, username: str) -> str:
        """Look up a username's global (cross-platform) player id from their
        profile page — required by every api.exophase.com call below."""
        url = f"{self.base_url}/user/{username}/"
        html = await self._get_html(client, url)
        soup = BeautifulSoup(html, "lxml")
        header = soup.select_one("div.user-header.global[data-playerid]")
        if not header or not header.get("data-playerid"):
            raise UserNotFoundError(f"Could not resolve a player id for '{username}'.")
        return header["data-playerid"]

    async def scrape_games(self, username: str) -> List[Dict[str, Any]]:
        """
        Scrape a user's full games list via the private
        `GET /public/player/{playerid}/games` endpoint the site's own Vue
        frontend uses.  Despite being served through a Cloudflare-fronted
        API, it responds to a plain HTTP client as long as it's called with
        the same headers a browser XHR would send — no headless browser
        required.
        """
        # The endpoint paginates at 50 games/page with no total-count field,
        # so keep requesting pages until one comes back short.
        raw_games: List[Dict[str, Any]] = []
        async with httpx.AsyncClient() as client:
            master_playerid = await self._resolve_master_playerid(client, username)
            page = 1
            while True:
                data = await self._get_json(
                    client,
                    f"{self.api_base_url}/public/player/{master_playerid}/games",
                    params={"page": page},
                )
                page_games = data.get("games", [])
                raw_games.extend(page_games)
                if len(page_games) < 50 or page >= 50:
                    break
                page += 1

        games: List[Dict[str, Any]] = []
        for g in raw_games:
            meta = g.get("meta", {})
            units = g.get("playtimeUnits", {}) or {}
            playtime_hours = round((units.get("hours", 0) or 0) + (units.get("minutes", 0) or 0) / 60, 2)
            env = meta.get("environment_slug", "")
            games.append({
                "game_title": meta.get("title", ""),
                "platform": _PLATFORM_ENV_MAP.get(env, env.capitalize() if env else ""),
                "completion_percentage": g.get("percent") or 0.0,
                "playtime_hours": playtime_hours,
                "earned_awards": g.get("earned_awards") or 0,
                "total_awards": g.get("total_awards") or meta.get("total_awards") or 0,
                "game_slug": self._slug_from_endpoint(meta.get("endpoint_awards")),
                "game_url": meta.get("endpoint_awards"),
                # Needed to fetch this game's earned-achievement timestamps —
                # NOT the same as the global master_playerid; the API reuses
                # the field name per-platform in this response.
                "player_id": g.get("master_playerid"),
                "master_id": g.get("master_id"),
            })
        return games

    async def scrape_recent_achievements(self, username: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Scrape the user's most recently earned achievements across every
        connected platform, via `GET /public/player/{playerid}/awards`.

        Each entry carries the earned timestamp (as Exophase displays it —
        the API doesn't expose a raw unix time here), icon, permalink and
        the game it belongs to.  The endpoint only ever returns a handful
        of the most recent unlocks — for a specific game's full history use
        `scrape_user_game_achievements` instead.
        """
        async with httpx.AsyncClient() as client:
            master_playerid = await self._resolve_master_playerid(client, username)
            data = await self._get_json(
                client, f"{self.api_base_url}/public/player/{master_playerid}/awards"
            )

        out: List[Dict[str, Any]] = []
        for a in data.get("awards", [])[:limit]:
            meta = a.get("meta", {}) or {}
            endpoint = a.get("endpoint")
            out.append({
                "id":            a.get("internal_award_id"),
                "name":          a.get("name", ""),
                "description":   a.get("description", ""),
                "rarity_percent": self._parse_float(a.get("average") or "0"),
                "icon_url":      a.get("image"),
                "url":           f"{self.base_url}{endpoint}" if endpoint else None,
                "earned_at":     a.get("earned"),
                "game_title":    meta.get("title", ""),
                "platform":      _PLATFORM_ENV_MAP.get(meta.get("environment_slug", ""), meta.get("environment_slug", "")),
            })
        return out

    async def scrape_summary(self, username: str, recent_limit: int = 5) -> Dict[str, Any]:
        """
        Profile info, per-platform breakdown, and the most recent unlocked
        achievements in one call — for a single initial-load round trip
        instead of the client firing off `/profile` and
        `/recent-achievements` separately. Runs both scrapes concurrently.
        """
        profile, recent = await asyncio.gather(
            self.scrape_profile(username),
            self.scrape_recent_achievements(username, limit=recent_limit),
        )
        profile["recent_achievements"] = recent
        return profile

    async def _fetch_earned_map(
        self, client: httpx.AsyncClient, player_id: Optional[int], master_id: Optional[int], total_earned: int
    ) -> Dict[int, Dict[str, Any]]:
        """`{masterAwardId: earned-item}` for one game, via the earned-awards API."""
        earned_by_id: Dict[int, Dict[str, Any]] = {}
        if not (player_id and master_id and total_earned):
            return earned_by_id
        earned_data = await self._get_json(
            client,
            f"{self.api_base_url}/public/player/{player_id}/game/{master_id}/earned",
            params={"limit": max(total_earned, 1)},
        )
        for item in earned_data.get("list", []):
            award_id = item.get("masterAwardId")
            if award_id is not None:
                earned_by_id[award_id] = item
        return earned_by_id

    @staticmethod
    def _apply_earned(catalogue: Dict[str, Any], earned_by_id: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """Stamp `earned` / `earned_at` / `earned_at_unix` onto each catalogue achievement in place."""
        for achievement in catalogue["achievements"]:
            earned = earned_by_id.get(achievement["id"])
            if earned:
                ts = earned.get("timestamp")
                achievement["earned"] = True
                achievement["earned_at_unix"] = ts
                achievement["earned_at"] = (
                    datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None
                )
            else:
                achievement["earned"] = False
                achievement["earned_at_unix"] = None
                achievement["earned_at"] = None
        return catalogue

    async def scrape_user_game_achievements(self, username: str, slug: str) -> Dict[str, Any]:
        """
        A single game's full achievement catalogue (name, description,
        points, rarity, icon, url — from the server-rendered catalogue page)
        merged with this user's own earned status and unlock timestamp for
        each one, pulled from `GET /public/player/{playerid}/game/{master_id}/earned`.

        Raises
        ------
        UserNotFoundError
            The user doesn't have this game (wrong slug, or never played it).
        """
        games = await self.scrape_games(username)
        game_entry = next((g for g in games if g.get("game_slug") == slug), None)
        if game_entry is None:
            raise UserNotFoundError(f"'{username}' has no tracked game with slug '{slug}'.")

        catalogue = await self.scrape_game_achievements(slug)
        async with httpx.AsyncClient() as client:
            earned_by_id = await self._fetch_earned_map(
                client, game_entry.get("player_id"), game_entry.get("master_id"), game_entry.get("earned_awards") or 0
            )
        return self._apply_earned(catalogue, earned_by_id)

    async def scrape_all_user_achievements(
        self, username: str, concurrency: int = 30, platform: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Every achievement the user has actually earned, across every game
        they've played, each with its name, description, points, rarity,
        icon, permalink and unlock timestamp.

        This fans out one catalogue scrape + one earned-awards API call per
        game that has at least one earned achievement (games with zero
        earned awards are skipped — nothing to report), bounded by
        `concurrency` concurrent requests and all sharing one pooled HTTP
        client, so games don't each pay for a fresh TLS handshake, with the
        catalogue fetch and the earned-awards fetch for each game running
        concurrently rather than back-to-back. For an account with hundreds
        of played games this is still genuinely slow (several seconds,
        potentially more) and puts a meaningful number of requests
        through Exophase's API — prefer `scrape_user_game_achievements` for
        a single game, or `scrape_recent_achievements` for a cheap recent-
        activity feed, when either fits the use case.

        Passing `platform` (a display name like "Steam" or an environment
        slug like "steam", case-insensitive) filters *before* fetching, not
        after — games on other platforms are skipped entirely rather than
        scraped and discarded, so it's also a real speedup, not just a
        smaller response.
        """
        games = await self.scrape_games(username)
        if platform:
            wanted = platform.strip().lower()
            wanted_display = _PLATFORM_ENV_MAP.get(wanted, "").lower()
            games = [
                g for g in games
                if g.get("platform", "").lower() == wanted or g.get("platform", "").lower() == wanted_display
            ]
        playable = [
            g for g in games
            if g.get("earned_awards") and g.get("game_slug") and g.get("player_id") and g.get("master_id")
        ]

        semaphore = asyncio.Semaphore(concurrency)

        async def fetch_one(client: httpx.AsyncClient, game: Dict[str, Any]) -> List[Dict[str, Any]]:
            async with semaphore:
                try:
                    catalogue, earned_by_id = await asyncio.gather(
                        self.scrape_game_achievements(game["game_slug"], client=client),
                        self._fetch_earned_map(
                            client, game["player_id"], game["master_id"], game["earned_awards"]
                        ),
                    )
                except ScraperError:
                    return []
            merged = self._apply_earned(catalogue, earned_by_id)
            out = []
            for achievement in merged["achievements"]:
                if achievement["earned"]:
                    entry = dict(achievement)
                    entry["game_title"] = merged["title"]
                    entry["game_slug"] = merged["slug"]
                    entry["platform"] = game["platform"]
                    out.append(entry)
            return out

        limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
        async with httpx.AsyncClient(limits=limits) as client:
            results = await asyncio.gather(*(fetch_one(client, g) for g in playable))

        all_earned: List[Dict[str, Any]] = [entry for page in results for entry in page]
        all_earned.sort(key=lambda a: a.get("earned_at_unix") or 0, reverse=True)
        return all_earned

    # ------------------------------------------------------------------
    # Game achievement catalogue
    # ------------------------------------------------------------------
    def _parse_game_achievements_html(self, html: str, slug: str, url: str) -> Dict[str, Any]:
        """CPU-bound HTML parsing half of `scrape_game_achievements`, split out
        so it can be run in a worker thread via `asyncio.to_thread` — parsing a
        ~100KB+ catalogue page with BeautifulSoup is slow enough to noticeably
        block the event loop otherwise, which matters when dozens of these run
        concurrently in `scrape_all_user_achievements`."""
        soup = BeautifulSoup(html, "lxml")
        awards = soup.select("li.award")
        if not awards:
            raise ScraperError(
                f"No achievements found at {url} — the slug may be wrong, or the "
                f"game may have no achievement list on Exophase."
            )

        # The game name is the page's first h2 — there is no h1 on this
        # template, and og:title carries " Achievements - <platform>" glued on.
        title_el = soup.select_one("h2")
        platform_el = soup.select_one(".exo-icon-collection-services + span, .generic span")

        out: List[Dict[str, Any]] = []
        for a in awards:
            classes = a.get("class") or []

            title_link = a.select_one(".award-title a")
            name = self._direct_text(title_link) if title_link else ""
            if not name:
                name = self._direct_text(a.select_one(".award-title")) if a.select_one(".award-title") else ""

            desc_el = a.select_one(".award-description")
            description = desc_el.get_text(" ", strip=True) if desc_el else ""

            img = a.select_one("img.award-image")
            icon_url = img.get("src") if img else None

            # Rarity is carried twice: as a data attribute and as display text.
            # The attribute is the reliable one — the text is localised and
            # carries the EXP value in the same string.
            out.append({
                "id":             self._parse_int(a.get("id") or a.get("data-master") or "0"),
                "index":          self._parse_int(a.get("data-award-id") or "0"),
                "name":           name,
                "description":    description,
                "points":         self._parse_int(a.get("data-points") or "0"),
                "rarity_percent": self._parse_float(a.get("data-average") or "0"),
                "earned_count":   self._parse_int(a.get("data-earned") or "0"),
                "secret":         "secret" in classes,
                "icon_url":       icon_url,
                "url":            title_link.get("href") if title_link else None,
            })

        return {
            "slug":         slug,
            "title":        title_el.get_text(strip=True) if title_el else slug,
            "platform":     platform_el.get_text(strip=True) if platform_el else None,
            "total":        len(out),
            "achievements": out,
            "source_url":   url,
        }

    async def scrape_game_achievements(
        self, slug: str, client: Optional[httpx.AsyncClient] = None
    ) -> Dict[str, Any]:
        """
        Scrape the full achievement catalogue for one game.

        Unlike the user games list, this page IS server-rendered — every award
        is present in the static HTML with its id, points, rarity and icon — so
        a plain HTTP client is enough and no headless browser is needed.

        `slug` is Exophase's own game slug, which carries the platform as a
        suffix (``hill-climb-racing-android`` is the Google Play listing of
        Hill Climb Racing).  Pass it exactly as it appears in the URL.

        An existing `client` can be passed in to reuse its connection pool —
        `scrape_all_user_achievements` does this across dozens of games so
        each one doesn't pay for a fresh TLS handshake.

        Returns
        -------
        dict
            ``{"slug", "title", "platform", "total", "achievements": [...]}``
            where each achievement carries ``id`` (Exophase's global award id),
            ``index`` (its position in the game's own list), ``name``,
            ``description``, ``points``, ``rarity_percent``, ``earned_count``,
            ``secret`` and ``icon_url``.  ``earned_count`` is user-scoped and
            reads 0 for an unauthenticated fetch — the catalogue is what this
            endpoint is for; who has unlocked what is not.

        Raises
        ------
        UserNotFoundError
            No such game/platform slug (404).
        ScraperError
            The page loaded but contained no award markup.
        """
        url = f"{self.base_url}/game/{slug}/achievements/"

        if client is not None:
            html = await self._get_html(client, url)
        else:
            async with httpx.AsyncClient(follow_redirects=True) as owned_client:
                html = await self._get_html(owned_client, url)

        return self._parse_game_achievements_html(html, slug, url)
