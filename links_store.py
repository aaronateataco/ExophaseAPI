"""
GitHub-backed JSON "database" for Discord ID <-> Exophase username links.

This service runs on Vercel, whose filesystem is read-only/ephemeral, so it
can't just keep a JSON file on local disk between requests. Instead it treats
a file in *this* GitHub repo (default: data/links.json) as the database,
reading and writing it through the GitHub Contents API. Every link/unlink
becomes a real commit to the repo - that's what makes new users show up
automatically for everyone else without a redeploy.

Setup (one-time):
  1. Create a fine-grained GitHub Personal Access Token scoped to just this
     repo, with "Contents: Read and write" permission.
  2. Set it as the GITHUB_TOKEN environment variable on the Vercel project
     (Project Settings -> Environment Variables). Never commit it.
  3. (Optional) Override GITHUB_REPO / GITHUB_BRANCH / LINKS_FILE_PATH if you
     want the database to live somewhere other than data/links.json on main.
"""

import base64
import json
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger("exophase_api.links_store")

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "aaronateataco/ExophaseAPI")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
LINKS_FILE_PATH = os.environ.get("LINKS_FILE_PATH", "data/links.json")

# Short TTL: reads within the same warm serverless instance are cheap, but
# this deliberately doesn't cache for long, since the whole point is that
# new links (possibly written by a *different* instance) show up quickly.
_CACHE_TTL_SECONDS = 30
_cache: Dict[str, Any] = {"data": None, "sha": None, "fetched_at": 0.0}


class LinksStoreError(Exception):
    """Raised when the GitHub-backed store can't be read or written."""


class LinksStoreConflict(LinksStoreError):
    """Raised when a write loses a race against a concurrent update."""


def _headers() -> Dict[str, str]:
    if not GITHUB_TOKEN:
        raise LinksStoreError(
            "GITHUB_TOKEN is not configured on this deployment - can't read or write the links database."
        )
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _contents_url() -> str:
    return f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{LINKS_FILE_PATH}"


async def _fetch_file() -> Tuple[Dict[str, Dict[str, Any]], Optional[str]]:
    """Returns (links_dict, sha). sha is None if the file doesn't exist yet."""
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(_contents_url(), params={"ref": GITHUB_BRANCH}, headers=_headers())

    if response.status_code == 404:
        return {}, None

    if response.status_code != 200:
        raise LinksStoreError(
            f"GitHub returned HTTP {response.status_code} reading {LINKS_FILE_PATH}: {response.text[:300]}"
        )

    payload = response.json()
    sha = payload.get("sha")
    raw = base64.b64decode(payload["content"]).decode("utf-8") if payload.get("content") else "{}"

    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        raise LinksStoreError(f"{LINKS_FILE_PATH} in the repo isn't valid JSON: {e}")

    return data, sha


async def _get_links(force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
    now = time.time()
    if not force_refresh and _cache["data"] is not None and (now - _cache["fetched_at"]) < _CACHE_TTL_SECONDS:
        return _cache["data"]

    data, sha = await _fetch_file()
    _cache["data"] = data
    _cache["sha"] = sha
    _cache["fetched_at"] = now
    return data


async def _write_links(data: Dict[str, Dict[str, Any]], message: str) -> None:
    body: Dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(json.dumps(data, indent=2, sort_keys=True).encode("utf-8")).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }
    if _cache["sha"]:
        body["sha"] = _cache["sha"]

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.put(_contents_url(), json=body, headers=_headers())

    if response.status_code == 409:
        # Our cached sha was stale (someone else wrote to the file since we
        # last read it) - let the caller refetch and retry once.
        raise LinksStoreConflict("The links file changed concurrently - retry the request.")

    if response.status_code not in (200, 201):
        raise LinksStoreError(
            f"GitHub returned HTTP {response.status_code} writing {LINKS_FILE_PATH}: {response.text[:300]}"
        )

    result = response.json()
    _cache["sha"] = result.get("content", {}).get("sha", _cache["sha"])
    _cache["data"] = data
    _cache["fetched_at"] = time.time()


async def get_all_links() -> Dict[str, Dict[str, Any]]:
    return await _get_links()


async def get_link(discord_id: str) -> Optional[str]:
    links = await _get_links()
    entry = links.get(discord_id)
    return entry.get("exophase_username") if entry else None


async def set_link(discord_id: str, exophase_username: str) -> None:
    links = dict(await _get_links())
    links[discord_id] = {"exophase_username": exophase_username, "updated_at": int(time.time())}

    try:
        await _write_links(links, f"Link Discord {discord_id} -> Exophase {exophase_username}")
    except LinksStoreConflict:
        links = dict(await _get_links(force_refresh=True))
        links[discord_id] = {"exophase_username": exophase_username, "updated_at": int(time.time())}
        await _write_links(links, f"Link Discord {discord_id} -> Exophase {exophase_username}")


async def delete_link(discord_id: str) -> bool:
    links = dict(await _get_links())
    if discord_id not in links:
        return False
    del links[discord_id]

    try:
        await _write_links(links, f"Unlink Discord {discord_id}")
    except LinksStoreConflict:
        links = dict(await _get_links(force_refresh=True))
        if discord_id not in links:
            return False
        del links[discord_id]
        await _write_links(links, f"Unlink Discord {discord_id}")

    return True
