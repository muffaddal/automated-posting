import httpx

from app.config import settings
from app.platforms.base import Platform


class Mastodon(Platform):
    name = "Mastodon"

    def credentials(self):
        return [settings.mastodon_base_url, settings.mastodon_access_token]

    async def publish(self, client: httpx.AsyncClient, message: str, link: str) -> str:
        r = await client.post(
            f"{settings.mastodon_base_url.rstrip('/')}/api/v1/statuses",
            headers={"Authorization": f"Bearer {settings.mastodon_access_token}"},
            data={"status": message, "visibility": "public"},
        )
        r.raise_for_status()
        return r.json()["url"]
