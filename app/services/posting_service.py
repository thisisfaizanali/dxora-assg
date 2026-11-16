import asyncio
import logging
from datetime import UTC, datetime

import httpx

from app.config import settings
from app.platforms.base import Platform, PlatformError
from app.schemas import PlatformResult

logger = logging.getLogger("app.posting")


async def post_to_all(message: str, platforms: list[Platform]) -> list[PlatformResult]:
    async with httpx.AsyncClient(
        timeout=settings.http_timeout_seconds,
        headers={"User-Agent": "automated-posting/1.0"},
    ) as client:
        return list(await asyncio.gather(*(_post_one(client, p, message) for p in platforms)))


async def _post_one(client: httpx.AsyncClient, platform: Platform, message: str) -> PlatformResult:
    try:
        url = await platform.post(client, message)
        public = await platform.check_public(client, url)
        now = datetime.now(UTC)
        logger.info("%s: posted %s (public=%s)", platform.name, url, public)
        return PlatformResult(
            platform=platform.name,
            status="success",
            posted_url=url,
            public_access=public,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            error=None,
        )
    except PlatformError as e:
        error = str(e)
    except httpx.TimeoutException:
        error = "Request timed out"
    except httpx.HTTPError as e:
        error = f"Network error: {type(e).__name__}"
    except Exception as e:
        logger.exception("%s: unexpected error", platform.name)
        error = f"Unexpected error: {type(e).__name__}"

    logger.warning("%s: failed: %s", platform.name, error)
    return PlatformResult(
        platform=platform.name,
        status="failed",
        posted_url=None,
        public_access=False,
        date=None,
        time=None,
        error=error,
    )
