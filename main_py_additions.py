# ---------------------------------------------------------------------------
# ADD-ON: Discord <-> Exophase account linking
#
# How to install:
#   1. Copy links_store.py and data/links.json into the repo root (next to
#      main.py). Add `httpx` to requirements.txt if it isn't already there
#      (scraper.py already imports it, so it almost certainly is).
#   2. Near the top of main.py, alongside the other imports, add:
#
#        import re
#        from links_store import get_link, set_link, delete_link, LinksStoreError, LINKS_FILE_PATH
#
#   3. Paste everything below into main.py (anywhere after the `app = FastAPI(...)`
#      block and the ErrorDetail model - e.g. right before the final
#      get_user_summary endpoint, or at the end of the file).
#   4. In Vercel, set the GITHUB_TOKEN environment variable (see links_store.py
#      docstring for how to create the token) and redeploy.
# ---------------------------------------------------------------------------

DISCORD_ID_PATTERN = re.compile(r"^\d{15,25}$")


class LinkRequest(BaseModel):
    discord_id: str = Field(..., description="The Discord user's snowflake ID.")
    exophase_username: str = Field(
        ..., min_length=1, max_length=64,
        description="The Exophase username to link to this Discord account."
    )


class LinkResponse(BaseModel):
    discord_id: str = Field(..., description="The Discord user's snowflake ID.")
    exophase_username: str = Field(..., description="The linked Exophase username.")


@app.post(
    "/api/v1/link",
    response_model=LinkResponse,
    responses={
        400: {"model": ErrorDetail, "description": "Invalid Discord ID, or the Exophase username doesn't exist/is private"},
        500: {"model": ErrorDetail, "description": "Failed to write to the links database"},
    },
    summary="Link a Discord account to an Exophase username",
    description=(
        "Registers (or overwrites) the Exophase username associated with a Discord user ID. "
        "The username is verified against a real, public Exophase profile before being saved. "
        f"The mapping is committed to `{LINKS_FILE_PATH}` in this GitHub repo, which acts as a "
        "lightweight public database that any client (e.g. the Equicord ExophaseAchievements "
        "plugin) can read back via GET /api/v1/link/{discord_id}.\n\n"
        "**No Discord authentication is performed.** This endpoint trusts whatever `discord_id` "
        "it's given - it has no way to confirm the caller actually controls that Discord account. "
        "A client that already knows its own logged-in user's ID (like the Equicord plugin, using "
        "Discord's own UserStore) is a reasonable caller; a raw unauthenticated HTTP request could "
        "in principle claim any Discord ID. If that becomes a problem, the natural fix is gating "
        "this endpoint behind Discord OAuth2 so it can verify the caller's identity server-side."
    ),
)
async def link_account(payload: LinkRequest, scraper: ExophaseScraper = Depends(get_scraper)):
    if not DISCORD_ID_PATTERN.match(payload.discord_id):
        raise HTTPException(status_code=400, detail="discord_id doesn't look like a valid Discord snowflake.")

    username = payload.exophase_username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="exophase_username can't be empty.")

    # Confirm this is a real, public Exophase profile before saving it -
    # keeps the database from filling up with typos and made-up names.
    try:
        await scraper.scrape_profile(username)
    except UserNotFoundError:
        raise HTTPException(status_code=400, detail=f"No public Exophase profile found for '{username}'.")
    except PrivateProfileError:
        raise HTTPException(status_code=400, detail=f"Exophase profile '{username}' is private.")
    except ScraperError as e:
        raise HTTPException(status_code=500, detail=f"Couldn't verify Exophase username: {e}")

    try:
        await set_link(payload.discord_id, username)
    except LinksStoreError as e:
        logger.error(f"Failed to write link for {payload.discord_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save link: {e}")

    return {"discord_id": payload.discord_id, "exophase_username": username}


@app.get(
    "/api/v1/link/{discord_id}",
    response_model=LinkResponse,
    responses={
        404: {"model": ErrorDetail, "description": "No Exophase account linked to this Discord ID"},
        500: {"model": ErrorDetail, "description": "Failed to read the links database"},
    },
    summary="Look up the Exophase username linked to a Discord account",
    description="Reads the current mapping out of the GitHub-backed links database (see POST /api/v1/link).",
)
async def get_link_route(discord_id: str = Path(..., description="Discord user snowflake ID")):
    try:
        username = await get_link(discord_id)
    except LinksStoreError as e:
        raise HTTPException(status_code=500, detail=f"Failed to read links database: {e}")

    if not username:
        raise HTTPException(status_code=404, detail="No Exophase account linked to this Discord ID.")

    return {"discord_id": discord_id, "exophase_username": username}


@app.delete(
    "/api/v1/link/{discord_id}",
    responses={
        404: {"model": ErrorDetail, "description": "No Exophase account linked to this Discord ID"},
        500: {"model": ErrorDetail, "description": "Failed to write to the links database"},
    },
    summary="Remove the Exophase link for a Discord account",
)
async def delete_link_route(discord_id: str = Path(..., description="Discord user snowflake ID")):
    try:
        removed = await delete_link(discord_id)
    except LinksStoreError as e:
        raise HTTPException(status_code=500, detail=f"Failed to update links database: {e}")

    if not removed:
        raise HTTPException(status_code=404, detail="No Exophase account linked to this Discord ID.")

    return {"status": "unlinked", "discord_id": discord_id}
