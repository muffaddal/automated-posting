from datetime import datetime, timezone

import httpx

from app.config import settings
from app.platforms.base import Platform

API = "https://bsky.social/xrpc"


def link_facet(text: str, link: str) -> dict:
    # bluesky wants utf-8 byte offsets, not python string indexes
    start = len(text[: text.index(link)].encode())
    return {
        "index": {"byteStart": start, "byteEnd": start + len(link.encode())},
        "features": [{"$type": "app.bsky.richtext.facet#link", "uri": link}],
    }


class Bluesky(Platform):
    name = "Bluesky"

    def credentials(self):
        return [settings.bluesky_handle, settings.bluesky_app_password]

    async def publish(self, client: httpx.AsyncClient, message: str, link: str) -> str:
        r = await client.post(
            f"{API}/com.atproto.server.createSession",
            json={"identifier": settings.bluesky_handle, "password": settings.bluesky_app_password},
        )
        r.raise_for_status()
        session = r.json()

        record = {
            "$type": "app.bsky.feed.post",
            "text": message,
            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "facets": [link_facet(message, link)],
        }
        r = await client.post(
            f"{API}/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {session['accessJwt']}"},
            json={"repo": session["did"], "collection": "app.bsky.feed.post", "record": record},
        )
        r.raise_for_status()
        rkey = r.json()["uri"].rsplit("/", 1)[-1]
        return f"https://bsky.app/profile/{session['handle']}/post/{rkey}"
