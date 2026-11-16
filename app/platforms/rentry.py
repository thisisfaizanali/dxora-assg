import httpx

from app.platforms.base import Platform, PlatformError, ensure_ok


class Rentry(Platform):
    name = "Rentry"

    async def post(self, client: httpx.AsyncClient, message: str) -> str:
        response = await client.post("https://rentry.co/api/new", data={"text": message})
        ensure_ok(response)
        try:
            data = response.json()
        except ValueError:
            raise PlatformError("Unexpected response from Rentry")
        if not isinstance(data, dict):
            raise PlatformError("Unexpected response from Rentry")
        if str(data.get("status")) != "200":
            raise PlatformError(f"Rentry: {data.get('content') or data.get('errors')}")
        url = data.get("url")
        if not url:
            raise PlatformError("Unexpected response from Rentry")
        return url
