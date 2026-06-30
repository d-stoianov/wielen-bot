"""Turn a Watch into a gaspedaal search URL and filter listings against it.

make/model become the URL path (gaspedaal uses /{merk}/{model}); year, price,
mileage, and fuel are enforced client-side on the fetched listings so we never
depend on guessing gaspedaal's query-parameter names.
"""

from __future__ import annotations

import re

from .models import Listing, Watch

_BASE_URL = "https://www.gaspedaal.nl"
_NEWEST_FIRST = "srt=df-a"

FUEL_CHOICES: tuple[str, ...] = ("petrol", "diesel", "electric", "hybrid")

# Canonical fuel -> substrings that may appear in a gaspedaal fuelType value
# (Dutch first) or that a user might type.
_FUEL_ALIASES: dict[str, tuple[str, ...]] = {
    "petrol": ("benzine", "petrol", "gasoline", "benzin"),
    "diesel": ("diesel",),
    "electric": ("elektrisch", "electric", "ev"),
    "hybrid": ("hybride", "hybrid", "phev"),
}

FUEL_LABELS: dict[str, str] = {
    "petrol": "Petrol",
    "diesel": "Diesel",
    "electric": "Electric",
    "hybrid": "Hybrid",
}


def normalize_fuel(text: str | None) -> str | None:
    """Map free-text fuel input (en or nl) to a canonical choice, or None."""
    if not text:
        return None
    value = text.strip().lower()
    if value in FUEL_CHOICES:
        return value
    for canonical, aliases in _FUEL_ALIASES.items():
        if any(alias in value for alias in aliases):
            return canonical
    return None


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def build_search_url(watch: Watch) -> str:
    """Build the gaspedaal search URL for a watch (newest first)."""
    if watch.url:
        return watch.url
    parts: list[str] = []
    if watch.make:
        parts.append(slugify(watch.make))
        if watch.model:
            parts.append(slugify(watch.model))
    path = "/".join(parts) if parts else "zoeken"
    return f"{_BASE_URL}/{path}?{_NEWEST_FIRST}"


def watch_matches(watch: Watch, listing: Listing) -> bool:
    """True if the listing satisfies the watch's client-side filters.

    Unknown listing fields (None) are treated as matching, so we err toward
    notifying rather than silently dropping a possibly-relevant car.
    """
    if watch.year_min is not None and listing.year is not None and listing.year < watch.year_min:
        return False
    if watch.year_max is not None and listing.year is not None and listing.year > watch.year_max:
        return False
    if watch.price_max is not None and listing.price is not None and listing.price > watch.price_max:
        return False
    if watch.km_max is not None and listing.mileage_km is not None and listing.mileage_km > watch.km_max:
        return False
    if watch.fuel and listing.fuel:
        aliases = _FUEL_ALIASES.get(watch.fuel, (watch.fuel,))
        if not any(alias in listing.fuel.lower() for alias in aliases):
            return False
    return True


def _eur(value: int) -> str:
    return f"€{value:,}".replace(",", ".")


def watch_summary(watch: Watch) -> str:
    """A compact, language-neutral one-line description of a watch's filters."""
    bits: list[str] = []
    title = " ".join(p for p in (watch.make, watch.model) if p)
    bits.append(title or (watch.url or "custom"))
    if watch.year_min or watch.year_max:
        lo = str(watch.year_min) if watch.year_min else "…"
        hi = str(watch.year_max) if watch.year_max else "…"
        bits.append(f"📅 {lo}–{hi}")
    if watch.price_max:
        bits.append(f"💶 ≤ {_eur(watch.price_max)}")
    if watch.km_max:
        bits.append(f"🛣 ≤ {watch.km_max:,} km".replace(",", "."))
    if watch.fuel:
        bits.append(f"⛽ {FUEL_LABELS.get(watch.fuel, watch.fuel)}")
    return " · ".join(bits)
