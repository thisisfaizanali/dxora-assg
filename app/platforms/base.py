from abc import ABC, abstractmethod

import httpx


class PlatformError(Exception):
    """Error whose message is safe to return to the client."""


def ensure_ok(response: httpx.Response) -> None:
    # Never include the request URL: some APIs carry tokens in it.
    if not response.is_success:
        raise PlatformError(f"HTTP {response.status_code}: {response.text[:200]}")


class Platform(ABC):
    name: str

    @abstractmethod
    async def post(self, client: httpx.AsyncClient, message: str) -> str:
        """Publish the message and return the public post URL."""

    async def check_public(self, client: httpx.AsyncClient, url: str) -> bool:
        try:
            response = await client.get(url, follow_redirects=True)
        except httpx.HTTPError:
            return False
        return response.status_code == 200
