import httpx

from app.platforms.base import Platform, PlatformError, ensure_ok


class PasteRs(Platform):
    name = "paste.rs"

    async def post(self, client: httpx.AsyncClient, message: str) -> str:
        response = await client.post("https://paste.rs/", content=message.encode())
        ensure_ok(response)
        if response.status_code == 206:
            raise PlatformError("paste.rs: paste was truncated")
        url = response.text.strip()
        if not url.startswith("http"):
            raise PlatformError("Unexpected response from paste.rs")
        return url
