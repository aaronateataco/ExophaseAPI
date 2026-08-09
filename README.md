# ExophaseAPI
Why isn't there an official API for exophase when it is the primary achievement hub for all platforms. Retroachievements is good but is only for retro games on consoles and doesn't support other modern systems and stuff and this scraper will be useful for a project I'm working on :)

---
title: Exophase Unofficial REST API Service
description: Prompt for Claude to build a standalone, reusable Exophase REST API using FastAPI.
---

# Exophase Unofficial FastAPI Wrapper

**Context for AI (Claude):**
I am building an open-source, unofficial REST API for Exophase.com to track cross-platform gaming achievements (Steam, Xbox, PlayStation, RetroAchievements, etc.). Exophase does not have a public API, so this project will act as a microservice layer. It will use web scraping (`httpx` and `BeautifulSoup4`) to extract public user data, and serve it via endpoints using `FastAPI`. 

This will be hosted on my personal GitHub as a standalone, universally integrable API service that I can use for various future projects (game launchers, Discord bots, web dashboards).

**Core Requirements:**
Please build a well-structured `FastAPI` application with the following architecture:

1. **Endpoint 1: `GET /api/v1/user/{username}/profile`**
   - Scrapes the main profile page (`https://www.exophase.com/user/{username}/`).
   - Returns a JSON response containing:
     - The user's Profile Picture (PFP) URL.
     - Total achievements, total playtime, and overall completion percentage.
     - The platforms connected to their account.

2. **Endpoint 2: `GET /api/v1/user/{username}/games`**
   - Scrapes the user's game list.
   - Returns a JSON array of game objects containing: Game Title, Platform (e.g., PSN, Steam), Individual Game Completion Percentage, Playtime, and the Exophase Game ID/URL.

3. **Backend Logic & Safety:**
   - Abstract the scraping logic into a separate `scraper.py` module to keep the API routes clean.
   - Implement basic in-memory caching (e.g., using `cachetools` or `functools.lru_cache`) for 5-10 minutes to prevent rate-limiting and avoid spamming Exophase servers.
   - Ensure the `httpx` client uses modern `User-Agent` headers.
   - Handle exceptions gracefully (e.g., return standard `404 Not Found` if a user doesn't exist, or `403 Forbidden` if the profile is private).

**Output Request:**
Please provide the complete project structure. Write the `main.py` (FastAPI routes), `scraper.py` (BeautifulSoup logic), and a `requirements.txt` file. Ensure the code is production-ready, typed, and well-commented.
