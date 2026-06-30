from __future__ import annotations

from wielenbot.fetchers.mapping import map_item


def test_maps_apify_shaped_item():
    raw = {
        "ad_id": "abc123",
        "url": "https://www.gaspedaal.nl/ad/abc123",
        "price": {"totaal": "€ 12.500", "totaal_inclusief_btw": 12500},
        "photos": {"foto_groot": "https://img/big.jpg", "foto_klein": "https://img/sm.jpg"},
        "date_posted": "2026-06-30",
        "provider": {
            "soort": "autoscout24",
            "aanbiedergegevens": {"plaats": "Amsterdam"},
        },
        "car_data": {
            "algemeen": {
                "merk": "Audi",
                "model": "A4 Avant",
                "bouwjaar": 2017,
                "tellerstand": "120.000 km",
                "brandstof": "Diesel",
            }
        },
    }

    listing = map_item(raw)

    assert listing is not None
    assert listing.ad_id == "abc123"
    assert listing.price == 12500
    assert listing.year == 2017
    assert listing.mileage_km == 120000
    assert listing.fuel == "Diesel"
    assert listing.location == "Amsterdam"
    assert listing.source == "autoscout24"
    assert listing.image_url == "https://img/big.jpg"
    assert "Audi" in listing.title and "A4" in listing.title


def test_falls_back_to_url_when_no_id():
    raw = {"url": "https://www.gaspedaal.nl/volkswagen/golf-2018", "prijs": 9000}
    listing = map_item(raw)
    assert listing is not None
    assert listing.ad_id == "https://www.gaspedaal.nl/volkswagen/golf-2018"
    assert listing.price == 9000
    # Title derived from slug.
    assert "golf" in listing.title.lower()


def test_returns_none_without_id_or_url():
    assert map_item({"price": {"totaal": 100}}) is None
    assert map_item("not a dict") is None  # type: ignore[arg-type]


def test_handles_flat_top_level_keys():
    raw = {
        "id": 555,
        "link": "https://x/ad/555",
        "prijs": "15000",
        "bouwjaar": "2019",
        "tellerstand": "80.000",
        "brandstof": "benzine",
    }
    listing = map_item(raw)
    assert listing is not None
    assert listing.ad_id == "555"
    assert listing.price == 15000
    assert listing.year == 2019
    assert listing.mileage_km == 80000
