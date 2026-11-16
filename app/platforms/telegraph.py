import httpx

from app.config import settings
from app.platforms.base import Platform, PlatformError, ensure_ok
from app.schemas import extract_links

API = "https://api.telegra.ph"


def _result(response: httpx.Response) -> dict:
    ensure_ok(response)
    try:
        data = response.json()
    except ValueError:
        raise PlatformError("Unexpected response from Telegraph")
    if not isinstance(data, dict):
        raise PlatformError("Unexpected response from Telegraph")
    if not data.get("ok"):
        raise PlatformError(f"Telegraph: {data.get('error', 'unknown error')}")
    result = data.get("result")
    if not isinstance(result, dict):
        raise PlatformError("Unexpected response from Telegraph")
    return result


class Telegraph(Platform):
    name = "Telegraph"

    async def post(self, client: httpx.AsyncClient, message: str) -> str:
        token = settings.telegraph_access_token
        if not token:
            account = _result(
                await client.post(
                    f"{API}/createAccount",
                    json={"short_name": "automated-posting", "author_name": settings.telegraph_author_name},
                )
            )
            token = account.get("access_token")
            if not token:
                raise PlatformError("Unexpected response from Telegraph")

        link = extract_links(message)[0]
        before, _, after = message.partition(link)
        title = " ".join((before + " " + after).split())[:60] or "Announcement"
        children = [
            c
            for c in (before, {"tag": "a", "attrs": {"href": link}, "children": [link]}, after)
            if c
        ]
        page = _result(
            await client.post(
                f"{API}/createPage",
                json={
                    "access_token": token,
                    "title": title,
                    "author_name": settings.telegraph_author_name,
                    "content": [{"tag": "p", "children": children}],
                },
            )
        )
        url = page.get("url")
        if not url:
            raise PlatformError("Unexpected response from Telegraph")
        return url
