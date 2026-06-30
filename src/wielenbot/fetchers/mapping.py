"""Tolerant mapping from a raw gaspedaal item (dict) to a normalized Listing.

Both the Apify actor and the Playwright network-capture path observe gaspedaal's
own data shape, which uses Dutch keys and nests details under `car_data`. The
exact key set drifts over time and differs slightly between sources, so every
lookup here is defensive: we probe a list of candidate keys and fall back to
`None` rather than raising. The only hard requirement is a stable `ad_id`.
"""

from __future__ import annotations

import re
from typing import Any

from ..models import Listing


def _first(d: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in d and d[key] not in (None, "", []):
            return d[key]
    return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    # Strings like "€ 12.500", "150.000 km", "12,500"
    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits else None


def _nested(raw: dict[str, Any], *path: str) -> Any:
    cur: Any = raw
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _price(raw: dict[str, Any]) -> int | None:
    price = raw.get("price")
    if isinstance(price, dict):
        return _to_int(_first(price, "totaal", "totaal_inclusief_btw", "amount", "value"))
    return _to_int(_first(raw, "prijs", "price", "amount"))


def _title(raw: dict[str, Any]) -> str | None:
    direct = _first(raw, "title", "titel", "naam", "name")
    if direct:
        return str(direct)
    algemeen = _nested(raw, "car_data", "algemeen") or {}
    if isinstance(algemeen, dict):
        make = _first(algemeen, "merk", "make")
        model = _first(algemeen, "model", "uitvoering", "type")
        parts = [str(p) for p in (make, model) if p]
        if parts:
            return " ".join(parts)
    # Last resort: derive from the URL slug.
    url = _first(raw, "url", "link")
    if url:
        slug = re.sub(r"https?://[^/]+/", "", str(url)).strip("/").split("?")[0]
        slug = slug.replace("-", " ").replace("/", " ").strip()
        if slug:
            return slug[:80]
    return None


def _algemeen_field(raw: dict[str, Any], *keys: str) -> Any:
    # Fields may live at the top level or under car_data.algemeen / car_data.motor.
    for container in (
        raw,
        _nested(raw, "car_data", "algemeen"),
        _nested(raw, "car_data", "motor"),
        _nested(raw, "car_data", "geschiedenis"),
    ):
        if isinstance(container, dict):
            value = _first(container, *keys)
            if value is not None:
                return value
    return None


def _source(raw: dict[str, Any]) -> str | None:
    provider = raw.get("provider")
    if isinstance(provider, dict):
        soort = _first(provider, "soort", "soort_slug")
        if soort:
            return str(soort)
    portals = raw.get("portals")
    if isinstance(portals, list) and portals:
        first = portals[0]
        if isinstance(first, dict):
            name = _first(first, "naam", "name", "portal", "slug")
            if name:
                return str(name)
        elif isinstance(first, str):
            return first
    return None


def _image(raw: dict[str, Any]) -> str | None:
    photos = raw.get("photos")
    if isinstance(photos, dict):
        return _first(photos, "foto_groot", "foto_xl", "foto_xxl", "foto_origineel", "foto_klein")
    media_photos = _nested(raw, "media", "photos")
    if isinstance(media_photos, list) and media_photos:
        first = media_photos[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return _first(first, "url", "src", "foto_groot")
    return _first(raw, "image", "thumbnail", "foto")


def _location(raw: dict[str, Any]) -> str | None:
    provider = raw.get("provider")
    if isinstance(provider, dict):
        details = provider.get("aanbiedergegevens")
        if isinstance(details, dict):
            loc = _first(details, "plaats", "stad", "city", "woonplaats", "location")
            if loc:
                return str(loc)
    return _first(raw, "plaats", "city", "location")


def map_item(raw: dict[str, Any]) -> Listing | None:
    """Map a raw gaspedaal item to a Listing, or None if it lacks a stable id."""
    if not isinstance(raw, dict):
        return None

    ad_id = _first(raw, "ad_id", "adId", "id", "advertentieId", "vipUrl", "license_plate")
    url = _first(raw, "url", "link", "vipUrl")
    if ad_id is None and url is None:
        return None
    if ad_id is None:
        ad_id = url  # URL is unique enough to dedup on if no id is exposed.

    return Listing(
        ad_id=str(ad_id),
        url=str(url) if url else "",
        title=_title(raw) or "Car listing",
        price=_price(raw),
        mileage_km=_to_int(_algemeen_field(raw, "tellerstand", "km_stand", "kmstand", "mileage", "km")),
        year=_to_int(_algemeen_field(raw, "bouwjaar", "jaar", "year", "registratiejaar")),
        fuel=(lambda f: str(f) if f else None)(_algemeen_field(raw, "brandstof", "fuel", "brandstof_slug")),
        location=_location(raw),
        source=_source(raw),
        image_url=_image(raw),
        date_posted=(lambda d: str(d) if d else None)(_first(raw, "date_posted", "datum", "geplaatst", "datePosted")),
    )
