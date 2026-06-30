"""Fetcher backed by the hosted Apify gaspedaal scraper.

Reliable from a datacenter/VPS IP because Apify runs real browsers behind
residential proxies, getting past gaspedaal's Akamai/DPG WAF. Paid.
"""

from __future__ import annotations

import logging

from apify_client import ApifyClient

from ..models import Listing, Search
from .mapping import map_item

logger = logging.getLogger(__name__)


class ApifyFetcher:
    def __init__(
        self,
        token: str,
        actor_id: str = "stealth_mode/gaspedaal-cars-search-scraper",
        *,
        use_proxy: bool = True,
        client: ApifyClient | None = None,
    ) -> None:
        if not token:
            raise ValueError("APIFY_TOKEN is required when FETCHER=apify")
        self._actor_id = actor_id
        self._use_proxy = use_proxy
        self._client = client or ApifyClient(token)

    def fetch(self, search: Search, max_items: int) -> list[Listing]:
        run_input = {
            "urls": [search.url],
            "ignore_url_failures": True,
            "max_items_per_url": max_items,
            "proxy": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]}
            if self._use_proxy
            else {"useApifyProxy": False},
        }
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
