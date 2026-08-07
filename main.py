import time
import logging
from typing import List, Dict, Tuple, Any, Optional
from fastapi import FastAPI, HTTPException, Path, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import our robust scraper
from scraper import ExophaseScraper, UserNotFoundError, PrivateProfileError, ScraperError, NotSupportedError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("exophase_api")

app = FastAPI(
    title="Exophase Unofficial REST API Service",
    description="A microservice layer to track cross-platform gaming achievements (Steam, Xbox, PSN, RetroAchievements, etc.)",
    version="1.0.0",
)

# Enable CORS for universal integration (game launchers, web dashboards, Discord bots)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# LIGHTWEIGHT IN-MEMORY TTL CACHE FOR ASYNC OPERATIONS
# --------------------------------------------------------------------------
class AsyncTTLMemoryCache:
    """
    A lightweight, dependency-free async-compatible TTL (Time-To-Live) cache.
    Prevents caching coroutines and ensures expired entries are cleaned up properly.
    """
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self.cache: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            timestamp, value = self.cache[key]
            if time.time() - timestamp < self.ttl:
                logger.info(f"Cache HIT for key: {key}")
                return value
            else:
                logger.info(f"Cache EXPIRED for key: {key}")
                del self.cache[key]
        return None

    def set(self, key: str, value: Any):
        logger.info(f"Cache SET for key: {key}")
        self.cache[key] = (time.time(), value)

# Initialize caches with 5-minute TTL (300 seconds)
profile_cache = AsyncTTLMemoryCache(ttl_seconds=300)
games_cache = AsyncTTLMemoryCache(ttl_seconds=300)
# A game's achievement catalogue changes only when the developer ships new
# ones, so it is cached far longer than the per-user views.
catalogue_cache = AsyncTTLMemoryCache(ttl_seconds=21600)

# Scraper Instance Dependency
def get_scraper() -> ExophaseScraper:
    return ExophaseScraper()

# --------------------------------------------------------------------------
# PYDANTIC SCHEMAS (DATA MODELS)
# --------------------------------------------------------------------------
class StatsModel(BaseModel):
    total_achievements: int = Field(..., description="Total count of achievements unlocked across all platforms.")
    total_playtime_hours: float = Field(..., description="Total recorded playtime hours.")
    overall_completion_percentage: float = Field(..., description="The user's aggregate completion percentage.")

class ProfileResponse(BaseModel):
    username: str = Field(..., description="The user's Exophase username.")
    profile_picture_url: Optional[str] = Field(None, description="Direct URL to the user's profile avatar image.")
    stats: StatsModel = Field(..., description="Aggregated gamer statistics.")
    connected_platforms: List[str] = Field(..., description="List of verified gaming networks connected to Exophase.")
    profile_url: str = Field(..., description="Direct link to the Exophase profile page.")

class GameItem(BaseModel):
    game_title: str = Field(..., description="The official name of the game.")
    platform: str = Field(..., description="The connected platform (e.g. Steam, PSN, Xbox, RetroAchievements).")
    completion_percentage: float = Field(..., description="Completion rate for this specific game.")
    playtime_hours: float = Field(..., description="Recorded hours of gameplay for this specific game.")
    game_slug: str = Field(..., description="The unique Exophase URL identifier or slug for the game.")
    game_url: str = Field(..., description="Direct link to Exophase page for the game.")

class Achievement(BaseModel):
    id: int = Field(..., description="Exophase's global award id.")
    index: int = Field(..., description="Position in the game's own achievement list.")
    name: str = Field(..., description="Achievement display name.")
    description: str = Field("", description="Achievement description; empty for some secrets.")
    points: int = Field(0, description="Points (XP) the platform awards for it.")
    rarity_percent: float = Field(0.0, description="Percentage of tracked players who have it.")
    earned_count: int = Field(0, description="User-scoped; 0 for an unauthenticated fetch.")
    secret: bool = Field(False, description="Hidden until unlocked on the platform.")
    icon_url: Optional[str] = Field(None, description="Direct URL to the 64x64 award icon.")
    url: Optional[str] = Field(None, description="Exophase permalink for the achievement.")

class GameAchievements(BaseModel):
    slug: str = Field(..., description="Exophase game slug, platform suffix included.")
    title: str = Field(..., description="Game display name.")
    platform: Optional[str] = Field(None, description="Platform the list belongs to, e.g. Google Play.")
    total: int = Field(..., description="Number of achievements in the list.")
    achievements: List[Achievement]
    source_url: str = Field(..., description="Page the data was scraped from.")

class ErrorDetail(BaseModel):
    detail: str = Field(..., description="Descriptive error message indicating what went wrong.")

# --------------------------------------------------------------------------
# REST API ENDPOINTS
# --------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root():
    """Welcome route with API details."""
    return {
        "service": "Exophase Unofficial REST API Service",
        "documentation": "/docs",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get(
    "/api/v1/user/{username}/profile",
    response_model=ProfileResponse,
    responses={
        404: {"model": ErrorDetail, "description": "User profile not found"},
        403: {"model": ErrorDetail, "description": "User profile is private"},
        500: {"model": ErrorDetail, "description": "Scraper or network failure"},
    },
    summary="Get Exophase Profile Details",
    description="Retrieves PFP, gaming platforms connected, and overall aggregate stats for a public Exophase user."
)
async def get_user_profile(
    username: str = Path(..., description="Exophase username (case-insensitive)", min_length=1),
    scraper: ExophaseScraper = Depends(get_scraper)
):
    cache_key = f"profile:{username.lower()}"
    
    # Check Cache
    cached_data = profile_cache.get(cache_key)
    if cached_data:
        return cached_data

    # Scrape and cache
    try:
        data = await scraper.scrape_profile(username)
        profile_cache.set(cache_key, data)
        return data
    except UserNotFoundError as e:
        logger.warning(f"Profile not found for username '{username}': {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except PrivateProfileError as e:
        logger.warning(f"Profile is private for username '{username}': {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except ScraperError as e:
        logger.error(f"Scraper error while fetching profile for '{username}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape Exophase profile: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error while fetching profile for '{username}'")
        raise HTTPException(status_code=500, detail=f"An unexpected internal error occurred: {e}")

@app.get(
    "/api/v1/user/{username}/games",
    response_model=List[GameItem],
    responses={
        404: {"model": ErrorDetail, "description": "User profile or games list not found"},
        403: {"model": ErrorDetail, "description": "User profile or games list is private"},
        500: {"model": ErrorDetail, "description": "Scraper or network failure"},
    },
    summary="Get Exophase Games and Achievements",
    description="Retrieves a list of games for an Exophase user, including individual completion percentage and playtime."
)
async def get_user_games(
    username: str = Path(..., description="Exophase username (case-insensitive)", min_length=1),
    scraper: ExophaseScraper = Depends(get_scraper)
):
    cache_key = f"games:{username.lower()}"
    
    # Check Cache
    cached_data = games_cache.get(cache_key)
    if cached_data:
        return cached_data

    # Scrape and cache
    try:
        games = await scraper.scrape_games(username)
        games_cache.set(cache_key, games)
        return games
    except NotSupportedError as e:
        logger.warning(f"Games list not supported: {e}")
        raise HTTPException(status_code=501, detail=str(e))
    except UserNotFoundError as e:
        logger.warning(f"Games list not found for username '{username}': {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except PrivateProfileError as e:
        logger.warning(f"Games list is private for username '{username}': {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except ScraperError as e:
        logger.error(f"Scraper error while fetching games for '{username}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape Exophase games: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error while fetching games for '{username}'")
        raise HTTPException(status_code=500, detail=f"An unexpected internal error occurred: {e}")


@app.get(
    "/api/v1/game/{slug}/achievements",
    response_model=GameAchievements,
    responses={
        404: {"model": ErrorDetail, "description": "No such game slug, or no achievement list for it"},
        500: {"model": ErrorDetail, "description": "Scraper or network failure"},
    },
    summary="Get a game's full achievement catalogue",
    description=(
        "Retrieves every achievement defined for one game, with points, rarity, "
        "secret flag and icon. Unlike the per-user games list, this page is "
        "server-rendered, so it needs no headless browser.\n\n"
        "The slug carries the platform as a suffix — pass "
        "`hill-climb-racing-android` for the Google Play listing of Hill Climb "
        "Racing, as it appears in the Exophase URL."
    ),
)
async def get_game_achievements(
    slug: str = Path(..., description="Exophase game slug, e.g. hill-climb-racing-android", min_length=1),
    scraper: ExophaseScraper = Depends(get_scraper),
):
    cache_key = f"catalogue:{slug.lower()}"

    cached_data = catalogue_cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        data = await scraper.scrape_game_achievements(slug)
        catalogue_cache.set(cache_key, data)
        return data
    except UserNotFoundError as e:
        logger.warning(f"No achievement list for slug '{slug}': {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except PrivateProfileError as e:
        logger.warning(f"Achievement list forbidden for slug '{slug}': {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except ScraperError as e:
        logger.error(f"Scraper error for slug '{slug}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape Exophase achievements: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error while fetching achievements for '{slug}'")
        raise HTTPException(status_code=500, detail=f"An unexpected internal error occurred: {e}")
