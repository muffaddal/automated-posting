from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    request_timeout: float = 15

    telegram_bot_token: str = ""
    telegram_channel: str = ""

    mastodon_base_url: str = "https://mastodon.social"
    mastodon_access_token: str = ""

    bluesky_handle: str = ""
    bluesky_app_password: str = ""

    github_token: str = ""

    devto_api_key: str = ""

    discord_webhook_url: str = ""
    discord_guild_id: str = ""


settings = Settings()
