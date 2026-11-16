import httpx

from app.config import settings
from app.platforms.base import Platform


class GitHubGist(Platform):
    name = "GitHub Gist"

    def credentials(self):
        return [settings.github_token]

    async def publish(self, client: httpx.AsyncClient, message: str, link: str) -> str:
        r = await client.post(
            "https://api.github.com/gists",
            headers={
                "Authorization": f"Bearer {settings.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "description": message,
                "public": True,
                "files": {"post.md": {"content": message}},
            },
        )
        r.raise_for_status()
        return r.json()["html_url"]
