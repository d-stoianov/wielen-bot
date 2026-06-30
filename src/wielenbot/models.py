"""Domain models shared across fetchers, store, and notifier."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Search:
    """A saved gaspedaal search the user wants to be notified about."""

    name: str
    url: str


@dataclass(frozen=True)
class Watch:
    """A named, filterable car watch managed by the user via the bot.

    make/model drive the gaspedaal search path; the remaining fields are applied
    as client-side filters on the fetched listings. `url` lets a power user pin a
    raw gaspedaal URL instead of make/model.
    """

    name: str
    make: str | None = None
    model: str | None = None
    year_min: int | None = None
    year_max: int | None = None
    price_max: int | None = None
    km_max: int | None = None
    fuel: str | None = None  # canonical: petrol | diesel | electric | hybrid
    url: str | None = None


@dataclass(frozen=True)
class Listing:
    """A normalized car listing, independent of which fetcher produced it.

    `ad_id` is the stable de-duplication key. Everything else is best-effort
    display data and may be missing depending on the source.
    """

    ad_id: str
    url: str
    title: str
    price: int | None = None  # euros, total
    mileage_km: int | None = None
    year: int | None = None
    fuel: str | None = None
    location: str | None = None
    source: str | None = None  # portal/provider, e.g. "autoscout24"
    image_url: str | None = None
    date_posted: str | None = None
