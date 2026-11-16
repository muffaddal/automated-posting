import asyncio
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.platforms.base import Platform
from app.schemas import PostResult

PLATFORMS: list[Platform] = []


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
        return PostResult(platform=platform.name, status="failed", error="missing credentials")
    try:
        url = await platform.publish(client, message, link)
    except Exception as e:
        return PostResult(platform=platform.name, status="failed", error=describe_error(e))

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
