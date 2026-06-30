"""Fetcher selection."""

from __future__ import annotations

from ..config import Config
from .base import Fetcher


def build_fetcher(config: Config) -> Fetcher:
    if config.fetcher == "apify":
        from .apify_fetcher import ApifyFetcher

        return ApifyFetcher(
            token=config.apify_token,
            actor_id=config.apify_actor_id,
            use_proxy=config.apify_use_proxy,
        )
    if config.fetcher == "playwright":
        from .playwright_fetcher import PlaywrightFetcher

        return PlaywrightFetcher(
            proxy=config.playwright_proxy,
            headless=config.playwright_headless,
        )
    raise ValueError(f"Unknown fetcher: {config.fetcher!r}")


__all__ = ["Fetcher", "build_fetcher"]
