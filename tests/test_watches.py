from __future__ import annotations

from wielenbot.models import Watch
from wielenbot.watches import (
    build_search_url,
    normalize_fuel,
    slugify,
    watch_matches,
    watch_summary,
)

from .conftest import make_listing


def test_slugify():
    assert slugify("Volkswagen") == "volkswagen"
    assert slugify("Mercedes-Benz") == "mercedes-benz"
    assert slugify("C Klasse") == "c-klasse"


def test_build_url_make_model():
    w = Watch(name="x", make="Audi", model="A4")
    assert build_search_url(w) == "https://www.gaspedaal.nl/audi/a4?srt=df-a"


def test_build_url_make_only():
    w = Watch(name="x", make="Audi")
    assert build_search_url(w) == "https://www.gaspedaal.nl/audi?srt=df-a"


def test_build_url_raw_url_wins():
    w = Watch(name="x", make="Audi", url="https://www.gaspedaal.nl/custom?srt=df-a")
    assert build_search_url(w) == "https://www.gaspedaal.nl/custom?srt=df-a"


def test_build_url_no_make():
    w = Watch(name="x")
    assert build_search_url(w) == "https://www.gaspedaal.nl/zoeken?srt=df-a"


def test_normalize_fuel():
    assert normalize_fuel("petrol") == "petrol"
    assert normalize_fuel("Benzine") == "petrol"
    assert normalize_fuel("elektrisch") == "electric"
    assert normalize_fuel("Hybride") == "hybrid"
    assert normalize_fuel("nonsense") is None
    assert normalize_fuel(None) is None


def test_matches_year_bounds():
    w = Watch(name="x", year_min=2016, year_max=2020)
    assert watch_matches(w, make_listing("1", year=2018))
    assert not watch_matches(w, make_listing("1", year=2014))
    assert not watch_matches(w, make_listing("1", year=2022))


def test_matches_price_and_km():
    w = Watch(name="x", price_max=15000, km_max=150000)
    assert watch_matches(w, make_listing("1", price=12000, mileage_km=100000))
    assert not watch_matches(w, make_listing("1", price=20000, mileage_km=100000))
    assert not watch_matches(w, make_listing("1", price=12000, mileage_km=200000))


def test_matches_fuel_dutch_value():
    w = Watch(name="x", fuel="petrol")
    assert watch_matches(w, make_listing("1", fuel="Benzine"))
    assert not watch_matches(w, make_listing("1", fuel="Diesel"))


def test_unknown_fields_pass():
    w = Watch(name="x", year_min=2016, price_max=15000)
    # listing missing year/price -> not dropped
    assert watch_matches(w, make_listing("1", year=None, price=None))


def test_summary_contains_filters():
    w = Watch(name="x", make="audi", model="a4", year_min=2016, year_max=2020,
              price_max=15000, km_max=150000, fuel="diesel")
    s = watch_summary(w)
    assert "audi a4" in s
    assert "2016" in s and "2020" in s
    assert "15.000" in s
    assert "150.000" in s
    assert "Diesel" in s
