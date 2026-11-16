import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.platforms.base import Platform
from app.platforms.bluesky import Bluesky
from app.platforms.devto import DevTo
from app.platforms.discord import Discord
from app.platforms.github_gist import GitHubGist
from app.platforms.mastodon import Mastodon
from app.platforms.telegram import Telegram
from app.schemas import PostResult

log = logging.getLogger("posting")

PLATFORMS: list[Platform] = [Telegram(), Mastodon(), Bluesky(), GitHubGist(), DevTo(), Discord()]


def describe_error(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        return f"HTTP {e.response.status_code}: {e.response.text[:200]}"
    if isinstance(e, httpx.TimeoutException):
        return "request timed out"
    if isinstance(e, httpx.RequestError):
        return f"connection error: {e.__class__.__name__}"
    return str(e) or e.__class__.__name__


async def run_one(platform: Platform, client: httpx.AsyncClient, message: str, link: str) -> PostResult:
    if not platform.is_configured():
        log.warning("%s skipped: missing credentials", platform.name)
        return PostResult(platform=platform.name, status="failed", error="missing credentials")
    try:
        url = await platform.publish(client, message, link)
    except Exception as e:
        log.warning("%s failed: %s", platform.name, describe_error(e))
        return PostResult(platform=platform.name, status="failed", error=describe_error(e))

    log.info("%s posted: %s", platform.name, url)
    now = datetime.now(timezone.utc)
    return PostResult(
        platform=platform.name,
        status="success",
        posted_url=url,
        public_access=platform.public,
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M:%S"),
    )


async def post_everywhere(message: str, link: str) -> list[PostResult]:
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        return await asyncio.gather(*(run_one(p, client, message, link) for p in PLATFORMS))
