from __future__ import annotations

from wielenbot.telegram import format_listing

from .conftest import make_listing


def test_format_includes_key_fields_and_link():
    listing = make_listing("1")
    msg = format_listing(listing, "Audi A4 onder 15k")

    assert "Audi A4 Avant" in msg
    assert "€12.500" in msg
    assert "2017" in msg
    assert "120.000 km" in msg
    assert "diesel" in msg
    assert "Amsterdam" in msg
    assert "Audi A4 onder 15k" in msg  # search name
    assert 'href="https://www.gaspedaal.nl/ad/1"' in msg


def test_link_label_defaults_to_english():
    msg = format_listing(make_listing("1"), "s")
    assert ">View listing</a>" in msg


def test_link_label_localized_to_dutch():
    msg = format_listing(make_listing("1"), "s", "nl")
    assert ">Bekijk advertentie</a>" in msg


def test_format_escapes_html():
    listing = make_listing("1", title="BMW <script> & co")
    msg = format_listing(listing, "search & filter")
    assert "<script>" not in msg
    assert "&lt;script&gt;" in msg
    assert "&amp;" in msg


def test_format_tolerates_missing_optional_fields():
    listing = make_listing(
        "1",
        price=None,
        year=None,
        mileage_km=None,
        fuel=None,
        location=None,
        source=None,
    )
    msg = format_listing(listing, "minimal")
    # Should still render title + link without raising.
    assert "Audi A4 Avant" in msg
    assert "View listing" in msg
