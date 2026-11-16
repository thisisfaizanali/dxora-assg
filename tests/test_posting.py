import asyncio
import re

import httpx
import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.platforms.base import Platform, PlatformError, ensure_ok
from app.services.posting_service import post_to_all

LINK = "https://example.com"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "PLATFORMS", [])
    return TestClient(main.app)


def post(client, message):
    return client.post("/posting", json={"message": message})


def assert_error(response, expected):
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert expected in [e["message"] for e in body["errors"]]


def test_message_too_long(client):
    message = "a" * 190 + f" {LINK}"
    assert_error(post(client, message), f"Message must not exceed 200 characters (got {len(message)}).")


def test_no_link(client):
    assert_error(post(client, "hello world"), "Message must contain exactly one CTA link (found 0).")


def test_two_links(client):
    assert_error(
        post(client, f"{LINK} and https://example.org"),
        "Message must contain exactly one CTA link (found 2).",
    )


def test_link_without_scheme(client):
    assert_error(post(client, "visit www.example.com"), "CTA link must start with http:// or https://.")


def test_link_without_dot(client):
    assert_error(post(client, "visit https://example"), "CTA link must have a valid domain (e.g. example.com).")


@pytest.mark.parametrize("message", ["", "   "])
def test_empty_message(client, message):
    assert_error(post(client, message), "Message must not be empty.")


def test_missing_message_field(client):
    response = client.post("/posting", json={})
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "message"


def test_message_as_number(client):
    response = client.post("/posting", json={"message": 123})
    assert response.status_code == 422
    assert response.json()["success"] is False


def test_exactly_200_chars_accepted(client):
    message = "a" * (200 - len(LINK) - 1) + f" {LINK}"
    assert len(message) == 200
    response = post(client, message)
    assert response.status_code == 200
    assert response.json() == {"success": False, "results": []}


def test_trailing_period_accepted(client):
    assert post(client, f"Visit {LINK}.").status_code == 200


class Ok(Platform):
    name = "ok"

    async def post(self, client, message):
        return "https://example.com/p/1"

    async def check_public(self, client, url):
        return True


class FailAuth(Platform):
    name = "fail_auth"

    async def post(self, client, message):
        raise PlatformError("Authentication failed")


class Crash(Platform):
    name = "crash"

    async def post(self, client, message):
        raise RuntimeError("secret detail")


def test_one_failure_does_not_stop_others():
    results = asyncio.run(post_to_all("msg", [Ok(), FailAuth(), Crash()]))
    assert [r.platform for r in results] == ["ok", "fail_auth", "crash"]
    ok, auth, crash = results
    assert ok.status == "success"
    assert ok.posted_url == "https://example.com/p/1"
    assert ok.public_access is True
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", ok.date)
    assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", ok.time)
    assert ok.error is None
    for failed, error in ((auth, "Authentication failed"), (crash, "Unexpected error: RuntimeError")):
        assert failed.status == "failed"
        assert failed.posted_url is None
        assert failed.date is None
        assert failed.time is None
        assert failed.public_access is False
        assert failed.error == error


def test_endpoint_success_flag(monkeypatch):
    monkeypatch.setattr(main, "PLATFORMS", [Ok(), FailAuth(), Crash()])
    body = post(TestClient(main.app), f"Visit {LINK}").json()
    assert body["success"] is True
    assert len(body["results"]) == 3


def test_all_failing_means_success_false(monkeypatch):
    monkeypatch.setattr(main, "PLATFORMS", [FailAuth(), Crash()])
    body = post(TestClient(main.app), f"Visit {LINK}").json()
    assert body["success"] is False
    assert [r["status"] for r in body["results"]] == ["failed", "failed"]


def test_ensure_ok_never_leaks_request_url():
    response = httpx.Response(
        500,
        text="boom",
        request=httpx.Request("POST", "https://api.example.com/botSECRET123/sendMessage"),
    )
    with pytest.raises(PlatformError) as exc:
        ensure_ok(response)
    assert "HTTP 500" in str(exc.value)
    assert "SECRET123" not in str(exc.value)
