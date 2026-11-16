import asyncio
import json

import httpx
import pytest

from app.platforms import PLATFORMS
from app.platforms.base import PlatformError
from app.platforms.dpaste import Dpaste
from app.platforms.ntfy import Ntfy
from app.platforms.paste_rs import PasteRs
from app.platforms.rentry import Rentry
from app.platforms.telegraph import Telegraph

LINK = "https://example.com"
MESSAGE = f"Check out our platform. {LINK} Grow today."


async def instant_sleep(_seconds):
    return None


def run(platform, handler, method="post"):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await getattr(platform, method)(client, MESSAGE)

    return asyncio.run(go())


def test_registry():
    names = [p.name for p in PLATFORMS]
    assert len(names) == 5
    assert len(set(names)) == 5


def test_telegraph_success(monkeypatch):
    monkeypatch.setattr("app.platforms.telegraph.settings.telegraph_access_token", "")
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append((request.method, str(request.url), body))
        if request.url.path == "/createAccount":
            return httpx.Response(200, json={"ok": True, "result": {"access_token": "tok"}})
        return httpx.Response(200, json={"ok": True, "result": {"url": "https://telegra.ph/x-01-01"}})

    assert run(Telegraph(), handler) == "https://telegra.ph/x-01-01"
    assert seen[0][:2] == ("POST", "https://api.telegra.ph/createAccount")
    method, url, body = seen[1]
    assert (method, url) == ("POST", "https://api.telegra.ph/createPage")
    assert body["access_token"] == "tok"
    assert body["title"] == "Check out our platform. Grow today."
    assert body["content"][0]["children"][1] == {"tag": "a", "attrs": {"href": LINK}, "children": [LINK]}


def test_telegraph_error(monkeypatch):
    monkeypatch.setattr("app.platforms.telegraph.settings.telegraph_access_token", "")
    handler = lambda request: httpx.Response(200, json={"ok": False, "error": "FLOOD_WAIT_5"})
    with pytest.raises(PlatformError, match="FLOOD_WAIT_5"):
        run(Telegraph(), handler)


def test_dpaste_success():
    def handler(request):
        assert (request.method, str(request.url)) == ("POST", "https://dpaste.org/api/")
        assert b"content=" in request.content and b"format=url" in request.content
        return httpx.Response(200, text="https://dpaste.org/abc\n")

    assert run(Dpaste(), handler) == "https://dpaste.org/abc"


def test_dpaste_http_error():
    with pytest.raises(PlatformError, match="HTTP 500"):
        run(Dpaste(), lambda request: httpx.Response(500, text="boom"))


def test_paste_rs_success():
    def handler(request):
        assert (request.method, str(request.url)) == ("POST", "https://paste.rs/")
        assert request.content == MESSAGE.encode()
        return httpx.Response(201, text="https://paste.rs/abc\n")

    assert run(PasteRs(), handler) == "https://paste.rs/abc"


def test_paste_rs_truncated():
    with pytest.raises(PlatformError, match="truncated"):
        run(PasteRs(), lambda request: httpx.Response(206, text="https://paste.rs/abc"))


def test_ntfy_success_and_public_check(monkeypatch):
    monkeypatch.setattr("app.platforms.ntfy.settings.ntfy_topic", "demo-topic")
    monkeypatch.setattr("app.platforms.ntfy.asyncio.sleep", instant_sleep)
    ntfy = Ntfy()

    def post_handler(request):
        assert (request.method, str(request.url)) == ("POST", "https://ntfy.sh/demo-topic")
        assert request.content == MESSAGE.encode()
        assert request.headers["Click"] == LINK
        return httpx.Response(200, json={"id": "m1"})

    url = run(ntfy, post_handler)
    assert url == "https://ntfy.sh/demo-topic"

    async def check(text):
        handler = lambda request: httpx.Response(200, text=text)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await ntfy.check_public(client, url)

    assert asyncio.run(check('{"id":"other"}\n{"id":"m1"}\n')) is True
    assert asyncio.run(check('{"id":"other"}\n')) is False


def test_ntfy_public_check_retries_until_cached(monkeypatch):
    monkeypatch.setattr("app.platforms.ntfy.asyncio.sleep", instant_sleep)
    ntfy = Ntfy()
    ntfy._last_id = "m1"
    bodies = iter(["", '{"id":"m1"}\n'])

    async def check():
        handler = lambda request: httpx.Response(200, text=next(bodies))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await ntfy.check_public(client, "https://ntfy.sh/demo-topic")

    assert asyncio.run(check()) is True


def test_rentry_success():
    def handler(request):
        assert (request.method, str(request.url)) == ("POST", "https://rentry.co/api/new")
        assert b"text=" in request.content
        return httpx.Response(200, json={"status": "200", "url": "https://rentry.co/abc"})

    assert run(Rentry(), handler) == "https://rentry.co/abc"


def test_rentry_status_error():
    handler = lambda request: httpx.Response(200, json={"status": "400", "content": "Bad text"})
    with pytest.raises(PlatformError, match="Bad text"):
        run(Rentry(), handler)
