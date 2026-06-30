"""Shared test helpers."""

from __future__ import annotations

from wielenbot.models import Listing


def make_listing(ad_id: str, **overrides: object) -> Listing:
    defaults = dict(
        ad_id=ad_id,
        url=f"https://www.gaspedaal.nl/ad/{ad_id}",
        title="Audi A4 Avant",
        price=12500,
        mileage_km=120000,
        year=2017,
        fuel="diesel",
        location="Amsterdam",
        source="autoscout24",
    )
    defaults.update(overrides)
    return Listing(**defaults)  # type: ignore[arg-type]
