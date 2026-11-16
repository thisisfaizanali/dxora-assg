import asyncio
import json

import httpx

from app.config import settings
from app.platforms.base import Platform, PlatformError, ensure_ok
from app.schemas import extract_links


class Ntfy(Platform):
    name = "ntfy"

    # ponytail: instance state assumes one request at a time per process (concurrent requests
    # could mix ids), upgrade path: return the id from post()
    _last_id: str | None = None

    async def post(self, client: httpx.AsyncClient, message: str) -> str:
        topic = settings.ntfy_topic
        response = await client.post(
            f"https://ntfy.sh/{topic}",
            content=message.encode(),
            headers={"Title": "New announcement", "Click": extract_links(message)[0]},
        )
        ensure_ok(response)
        try:
            message_id = response.json()["id"]
        except (ValueError, KeyError, TypeError):
            raise PlatformError("Unexpected response from ntfy")
        self._last_id = message_id
        return f"https://ntfy.sh/{topic}"

    async def check_public(self, client: httpx.AsyncClient, url: str) -> bool:
        # ntfy.sh writes to its cache slightly after replying, so the first poll can miss the message
        for attempt in range(3):
            if attempt:
                await asyncio.sleep(1)
            if await self._is_stored(client, url):
                return True
        return False

    async def _is_stored(self, client: httpx.AsyncClient, url: str) -> bool:
        try:
            response = await client.get(f"{url}/json?poll=1")
        except httpx.HTTPError:
            return False
        if response.status_code != 200 or not self._last_id:
            return False
        for line in response.text.splitlines():
            try:
                if json.loads(line).get("id") == self._last_id:
                    return True
            except (ValueError, AttributeError):
                continue
        return False
