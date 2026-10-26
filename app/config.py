from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    public_base_url: str = "https://awtik.ru"

    # Applies to every request except /healthz. A normal page load fetches
    # roughly 15–20 assets, so the default is generous for people and still
    # stops naive request floods.
    rate_limit_requests: int = 120
    rate_limit_window: int = 60
    trust_proxy_headers: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_ignore_empty=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
