import httpx

from app.platforms.base import Platform, PlatformError, ensure_ok


class Dpaste(Platform):
    name = "dpaste"

    async def post(self, client: httpx.AsyncClient, message: str) -> str:
        response = await client.post(
            "https://dpaste.org/api/",
            data={"content": message, "format": "url", "expires": "2592000"},
        )
        ensure_ok(response)
        url = response.text.strip()
        if not url.startswith("https://"):
            raise PlatformError("Unexpected response from dpaste")
        return url
