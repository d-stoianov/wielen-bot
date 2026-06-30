"""Fetcher backed by a hosted Apify gaspedaal scraper.

Reliable from a datacenter/VPS IP because the actor gets past gaspedaal's
Akamai/DPG WAF for us. Two actors are supported; their input schemas differ, so
the run-input is built per actor:

- unfenced-group/gaspedaal-nl-scraper   (default) — pay-per-result, free WAF
  bypass; input uses `startUrls` + `maxItems`.
- stealth_mode/gaspedaal-cars-search-scraper — flat monthly rental; input uses
  `urls` + `max_items_per_url` and benefits from Apify residential proxy.
"""

from __future__ import annotations

import logging

from apify_client import ApifyClient

from ..models import Listing, Search
from .mapping import map_item

logger = logging.getLogger(__name__)


def _input_unfenced(url: str, max_items: int, use_proxy: bool) -> dict:
    run_input: dict = {
        "startUrls": [{"url": url}],
        "maxItems": max_items,
        "requestDelayMs": 1000,
    }
    # The actor's built-in bypass is free; only attach Apify proxy if asked.
    if use_proxy:
        run_input["proxyConfiguration"] = {"useApifyProxy": True}
    return run_input


def _input_stealth(url: str, max_items: int, use_proxy: bool) -> dict:
    return {
        "urls": [url],
        "ignore_url_failures": True,
        "max_items_per_url": max_items,
        "proxy": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]}
        if use_proxy
        else {"useApifyProxy": False},
    }


_INPUT_BUILDERS = {
    "unfenced-group/gaspedaal-nl-scraper": _input_unfenced,
    "stealth_mode/gaspedaal-cars-search-scraper": _input_stealth,
}


class ApifyFetcher:
    def __init__(
        self,
        token: str,
        actor_id: str = "unfenced-group/gaspedaal-nl-scraper",
        *,
        use_proxy: bool = False,
        client: ApifyClient | None = None,
    ) -> None:
        if not token:
            raise ValueError("APIFY_TOKEN is required when FETCHER=apify")
        self._actor_id = actor_id
        self._use_proxy = use_proxy
        self._client = client or ApifyClient(token)

    def fetch(self, search: Search, max_items: int) -> list[Listing]:
        build_input = _INPUT_BUILDERS.get(self._actor_id, _input_unfenced)
        run_input = build_input(search.url, max_items, self._use_proxy)
        logger.info("Apify run starting for %r (max %d)", search.name, max_items)
        run = self._client.actor(self._actor_id).call(run_input=run_input)
        if run is None:
            raise RuntimeError(f"Apify actor {self._actor_id} returned no run for {search.name!r}")

        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            raise RuntimeError(f"Apify run for {search.name!r} produced no dataset")

        listings: list[Listing] = []
        for raw in self._client.dataset(dataset_id).iterate_items():
            listing = map_item(raw)
            if listing is not None:
                listings.append(listing)
        logger.info("Apify returned %d listings for %r", len(listings), search.name)
        return listings
