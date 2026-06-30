from __future__ import annotations

import pytest

from wielenbot.config import load_searches


def test_load_searches_parses_entries(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """
searches:
  - name: "Audi A4"
    url: "https://www.gaspedaal.nl/audi/a4?srt=df-a"
  - name: "VW Golf"
    url: "https://www.gaspedaal.nl/volkswagen/golf?srt=df-a"
"""
    )
    searches = load_searches(cfg)
    assert len(searches) == 2
    assert searches[0].name == "Audi A4"
    assert searches[1].url.endswith("srt=df-a")


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_searches(tmp_path / "nope.yaml")


def test_empty_searches_raises(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("searches: []\n")
    with pytest.raises(ValueError):
        load_searches(cfg)


def test_entry_missing_url_raises(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text('searches:\n  - name: "no url"\n')
    with pytest.raises(ValueError):
        load_searches(cfg)
