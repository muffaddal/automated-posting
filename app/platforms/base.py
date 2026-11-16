import httpx


class Platform:
    name: str = ""
    public: bool = True

    def credentials(self) -> list[str]:
        return []

    def is_configured(self) -> bool:
        return all(self.credentials())

    async def publish(self, client: httpx.AsyncClient, message: str, link: str) -> str:
        """Post the message and return the URL of the published content."""
        raise NotImplementedError
