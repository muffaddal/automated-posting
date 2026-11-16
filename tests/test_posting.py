import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.platforms.base import Platform
from app.platforms.bluesky import Bluesky, link_facet
from app.platforms.devto import make_title
from app.platforms.discord import Discord
from app.platforms.github_gist import GitHubGist
from app.platforms.mastodon import Mastodon
from app.platforms.telegram import Telegram
from app.services import posting_service

client = TestClient(app)


class Fake(Platform):
    def __init__(self, name, url=None, exc=None):
        self.name, self.url, self.exc = name, url, exc

    async def publish(self, client, message, link):
        if self.exc:
            raise self.exc
        return self.url


@pytest.fixture(autouse=True)
def no_real_platforms(monkeypatch):
    monkeypatch.setattr(posting_service, "PLATFORMS", [Fake("A", url="https://a.com/1")])


@pytest.mark.parametrize("message", [
    "no link here",
    "two links https://a.com and https://b.com",
    "bad host https://localhost",
    "broken https://",
    "ftp only ftp://files.example.com",
    "   ",
    "x" * 190 + " https://example.com",
])
def test_rejects_invalid_messages(message):
    assert client.post("/posting", json={"message": message}).status_code == 422


def test_rejects_missing_message():
    assert client.post("/posting", json={}).status_code == 422


def test_accepts_exactly_200_chars():
    msg = "x" * 180 + " https://example.com"
    assert len(msg) == 200
    assert client.post("/posting", json={"message": msg}).status_code == 200


def test_valid_message_returns_results():
    r = client.post("/posting", json={"message": "Check us out https://example.com."})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["results"][0]["platform"] == "A"
    assert body["results"][0]["posted_url"] == "https://a.com/1"


def test_one_failure_does_not_stop_others(monkeypatch):
    monkeypatch.setattr(posting_service, "PLATFORMS", [
        Fake("A", url="https://a.com/1"),
        Fake("B", exc=RuntimeError("boom")),
        Fake("C", exc=httpx.ReadTimeout("slow")),
        Fake("D", url="https://d.com/1"),
    ])
    results = asyncio.run(posting_service.post_everywhere("hi https://x.com", "https://x.com"))
    by_name = {r.platform: r for r in results}

    assert by_name["A"].status == "success" and by_name["A"].date and by_name["A"].time
    assert by_name["B"].status == "failed" and by_name["B"].error == "boom"
    assert by_name["B"].posted_url is None and by_name["B"].date is None
    assert by_name["C"].error == "request timed out"
    assert by_name["D"].status == "success"


def test_all_failed_means_success_false(monkeypatch):
    monkeypatch.setattr(posting_service, "PLATFORMS", [Fake("A", exc=RuntimeError("nope"))])
    body = client.post("/posting", json={"message": "hi https://x.com"}).json()
    assert body["success"] is False


def test_unconfigured_platform_fails_cleanly(monkeypatch):
    monkeypatch.setattr(settings, "github_token", "")
    monkeypatch.setattr(posting_service, "PLATFORMS", [GitHubGist()])
    result = client.post("/posting", json={"message": "hi https://x.com"}).json()["results"][0]
    assert result == {
        "platform": "GitHub Gist", "status": "failed", "posted_url": None,
        "public_access": False, "date": None, "time": None, "error": "missing credentials",
    }


def test_bluesky_facet_uses_byte_offsets():
    text = "héllo 🚀 https://x.com"
    f = link_facet(text, "https://x.com")["index"]
    assert text.encode()[f["byteStart"]:f["byteEnd"]] == b"https://x.com"
    assert f["byteStart"] != text.index("https://x.com")


def test_devto_title():
    assert make_title("Grow your business https://x.com", "https://x.com") == "Grow your business"
    assert make_title("https://x.com", "https://x.com") == "Quick update"


def fake_api(request: httpx.Request) -> httpx.Response:
    host, path = request.url.host, request.url.path
    if host == "api.telegram.org":
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 7, "chat": {"username": "chan"}}})
    if host == "mastodon.test":
        return httpx.Response(200, json={"url": "https://mastodon.test/@me/1"})
    if path.endswith("createSession"):
        return httpx.Response(200, json={"accessJwt": "jwt", "did": "did:plc:abc", "handle": "me.bsky.social"})
    if path.endswith("createRecord"):
        return httpx.Response(200, json={"uri": "at://did:plc:abc/app.bsky.feed.post/3kxyz"})
    if host == "api.github.com":
        return httpx.Response(201, json={"html_url": "https://gist.github.com/me/abc"})
    if host == "discord.test":
        return httpx.Response(200, json={"id": "99", "channel_id": "55"})
    return httpx.Response(404)


@pytest.mark.parametrize("platform, expected", [
    (Telegram(), "https://t.me/chan/7"),
    (Mastodon(), "https://mastodon.test/@me/1"),
    (Bluesky(), "https://bsky.app/profile/me.bsky.social/post/3kxyz"),
    (GitHubGist(), "https://gist.github.com/me/abc"),
    (Discord(), "https://discord.com/channels/11/55/99"),
])
def test_platforms_build_post_urls(monkeypatch, platform, expected):
    monkeypatch.setattr(settings, "mastodon_base_url", "https://mastodon.test")
    monkeypatch.setattr(settings, "discord_webhook_url", "https://discord.test/api/webhooks/1/x")
    monkeypatch.setattr(settings, "discord_guild_id", "11")

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(fake_api)) as c:
            return await platform.publish(c, "hi https://x.com", "https://x.com")

    assert asyncio.run(go()) == expected
