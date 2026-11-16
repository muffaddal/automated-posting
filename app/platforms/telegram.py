import httpx

from app.config import settings
from app.platforms.base import Platform


class Telegram(Platform):
    name = "Telegram"

    def credentials(self):
        return [settings.telegram_bot_token, settings.telegram_channel]

    async def publish(self, client: httpx.AsyncClient, message: str, link: str) -> str:
        r = await client.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={"chat_id": settings.telegram_channel, "text": message},
        )
        r.raise_for_status()
        result = r.json()["result"]
        username = result["chat"].get("username")
        if not username:
            raise RuntimeError("message sent but channel is private, no public link")
        return f"https://t.me/{username}/{result['message_id']}"
