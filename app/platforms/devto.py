import httpx

from app.config import settings
from app.platforms.base import Platform


def make_title(message: str, link: str) -> str:
    title = " ".join(message.replace(link, "").split())
    if len(title) > 60:
        title = title[:57].rsplit(" ", 1)[0] + "..."
    return title or "Quick update"


class DevTo(Platform):
    name = "Dev.to"

    def credentials(self):
        return [settings.devto_api_key]

    async def publish(self, client: httpx.AsyncClient, message: str, link: str) -> str:
        r = await client.post(
            "https://dev.to/api/articles",
            headers={"api-key": settings.devto_api_key, "Accept": "application/vnd.forem.api-v1+json"},
            json={
                "article": {
                    "title": make_title(message, link),
                    "body_markdown": message,
                    "published": True,
                    "canonical_url": link,
                }
            },
        )
        r.raise_for_status()
        return r.json()["url"]
