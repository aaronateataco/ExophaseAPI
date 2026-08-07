# ExophaseScraper — Unofficial Exophase REST API

An unofficial FastAPI microservice that scrapes public Exophase.com profiles and serves the data as a typed JSON REST API. Useful for game launchers, Discord bots, and web dashboards.

## Stack

- **Python 3.12**
- **FastAPI** — REST API framework with auto-generated Swagger docs
- **httpx** — async HTTP client for scraping
- **BeautifulSoup4** — HTML parsing
- **uvicorn** — ASGI server

## Run

```
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

The workflow `Start application` is pre-configured and starts this command automatically.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Service info |
| GET | `/docs` | Interactive Swagger UI |
| GET | `/api/v1/user/{username}/profile` | Avatar, stats, connected platforms |
| GET | `/api/v1/user/{username}/games` | ⚠️ Returns 501 — games are JS-rendered (see below) |

### Example

```
GET /api/v1/user/FoxStorm1/profile
```

```json
{
  "username": "FoxStorm1",
  "profile_picture_url": "https://www.exophase.com/forums/data/avatars/...",
  "stats": {
    "total_achievements": 731,
    "total_playtime_hours": 4385.0,
    "overall_completion_percentage": 15.38
  },
  "connected_platforms": ["Steam", "RetroAchievements", "Google Play", "Epic Games", "Nintendo"],
  "profile_url": "https://www.exophase.com/user/FoxStorm1/"
}
```

## Known Limitations

**Games list is not scrapable** — Exophase loads game data exclusively via a Cloudflare-protected JSON API (`api.exophase.com`) consumed by a Vue.js SPA. A server-side HTML scraper cannot pass the JS challenge. To support the games endpoint, a headless browser (Playwright or Selenium) would be needed.

## Caching

Responses are cached in-memory for 5 minutes (300 s) per username to avoid rate-limiting Exophase.

## Project Structure

```
main.py          — FastAPI routes, Pydantic schemas, caching layer
scraper.py       — ExophaseScraper class, HTML parsing logic
requirements.txt — Python dependencies
```

## User Preferences

- Keep the existing project structure (main.py / scraper.py split).
