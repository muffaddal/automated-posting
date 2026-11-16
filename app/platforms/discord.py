import httpx

from app.config import settings
from app.platforms.base import Platform


class Discord(Platform):
    name = "Discord"
    public = False  # only visible to server members

    def credentials(self):
        return [settings.discord_webhook_url, settings.discord_guild_id]

    async def publish(self, client: httpx.AsyncClient, message: str, link: str) -> str:
        r = await client.post(settings.discord_webhook_url, params={"wait": "true"}, json={"content": message})
        r.raise_for_status()
        msg = r.json()
        return f"https://discord.com/channels/{settings.discord_guild_id}/{msg['channel_id']}/{msg['id']}"
