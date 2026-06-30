"""Free fetcher using a real headless Chromium via Playwright.

Loading the page in a real browser solves gaspedaal's Akamai JS challenge. From
a datacenter/VPS IP Akamai usually still blocks by ASN, so set PLAYWRIGHT_PROXY
to a residential/mobile proxy. From a residential IP (home/Pi) it works as-is.

Strategy: we don't hand-write CSS selectors (gaspedaal is a JS app whose markup
changes). Instead we capture the JSON the page's own frontend fetches, find the
array(s) of listing-shaped objects, and run them through the shared mapper — the
same normalization the Apify path uses. If gaspedaal changes its API shape, the
mapper's defensive key probing is the single place to adjust.
"""

from __future__ import annotations

import logging
from typing import Any

from ..models import Listing, Search
from .mapping import map_item

logger = logging.getLogger(__name__)

# A JSON object is "listing-shaped" if it carries an id-ish key and price/url.
_ID_KEYS = ("ad_id", "adId", "id", "advertentieId", "license_plate")
_CORROBORATING_KEYS = ("price", "prijs", "url", "vipUrl", "car_data", "photos")


def _looks_like_listing(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    has_id = any(k in obj for k in _ID_KEYS)
    has_other = any(k in obj for k in _CORROBORATING_KEYS)
    return has_id and has_other


def _collect_listings(node: Any, out: list[dict[str, Any]]) -> None:
    """Walk an arbitrary JSON tree collecting listing-shaped dicts."""
    if isinstance(node, list):
        if node and all(_looks_like_listing(x) for x in node):
            out.extend(node)
            return
        for item in node:
            _collect_listings(item, out)
    elif isinstance(node, dict):
        if _looks_like_listing(node):
            out.append(node)
            return
        for value in node.values():
            _collect_listings(value, out)


class PlaywrightFetcher:
    def __init__(
        self,
        *,
        proxy: str | None = None,
        headless: bool = True,
        nav_timeout_ms: int = 45000,
    ) -> None:
        self._proxy = proxy
        self._headless = headless
        self._nav_timeout_ms = nav_timeout_ms

    def fetch(self, search: Search, max_items: int) -> list[Listing]:
        # Imported lazily so the module (and tests) load without Playwright installed.
        from playwright.sync_api import sync_playwright

        captured: list[dict[str, Any]] = []

        launch_kwargs: dict[str, Any] = {"headless": self._headless}
        if self._proxy:
            launch_kwargs["proxy"] = {"server": self._proxy}

        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context(
                locale="nl-NL",
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            def on_response(response: Any) -> None:
                ctype = response.headers.get("content-type", "")
                if "application/json" not in ctype:
                    return
                try:
                    body = response.json()
                except Exception:  # noqa: BLE001 - non-JSON or aborted body
                    return
                _collect_listings(body, captured)

            page.on("response", on_response)

            page.goto(search.url, wait_until="networkidle", timeout=self._nav_timeout_ms)

            if not captured:
                # Fall back to hydration state embedded in the document.
                for expr in ("window.__NUXT__", "window.__NEXT_DATA__"):
                    try:
                        state = page.evaluate(f"() => {expr}")
                    except Exception:  # noqa: BLE001
                        state = None
                    if state:
                        _collect_listings(state, captured)
                    if captured:
                        break

            browser.close()

        if not captured:
            raise RuntimeError(
                f"Playwright captured no listings for {search.name!r}. Gaspedaal likely "
                "blocked the request (datacenter IP) — set PLAYWRIGHT_PROXY to a "
                "residential proxy, or switch FETCHER=apify."
            )

        listings: list[Listing] = []
        seen_ids: set[str] = set()
        for raw in captured:
            listing = map_item(raw)
            if listing is None or listing.ad_id in seen_ids:
                continue
            seen_ids.add(listing.ad_id)
            listings.append(listing)
            if len(listings) >= max_items:
                break

        logger.info("Playwright returned %d listings for %r", len(listings), search.name)
        return listings
