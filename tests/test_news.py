import io
import json
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

import exchange_calendars as xc
import pandas as pd
import pytest
import yfinance as yf

import stock_research.data as data


@pytest.fixture
def live_feed(tmp_path, monkeypatch):
    """Run the live bundle path with a fixed clock, synthetic bars and local RSS."""
    now = datetime(2026, 10, 30, 18, tzinfo=ZoneInfo("America/New_York"))

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now.astimezone(tz)

    sessions = xc.get_calendar("XNYS").sessions_in_range("2026-07-01", "2026-10-30")
    history = pd.DataFrame(
        {"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0, "Volume": 1000.0},
        index=sessions,
    )
    calls = {"prices": 0, "rss": 0}
    feed = {"items": []}

    def ticker(symbol):
        assert symbol == "GOOGL"
        calls["prices"] += 1
        return SimpleNamespace(history=lambda **kwargs: history)

    def urlopen(request, timeout):
        calls["rss"] += 1
        channel = ET.Element("channel")
        for title, published in feed["items"]:
            item = ET.SubElement(channel, "item")
            if title is not None:
                ET.SubElement(item, "title").text = title
            ET.SubElement(item, "link").text = "https://example.com/news"
            ET.SubElement(item, "pubDate").text = published
            ET.SubElement(item, "source").text = "Yahoo Finance"
        root = ET.Element("rss")
        root.append(channel)
        return io.BytesIO(ET.tostring(root))

    monkeypatch.setattr(data, "ROOT", tmp_path)
    monkeypatch.setattr(data, "datetime", Clock)
    monkeypatch.setattr(data, "urlopen", urlopen)
    monkeypatch.setattr(yf, "Ticker", ticker)

    def set_titles(titles):
        feed["items"] = [(title, "Fri, 30 Oct 2026 16:00:00 -0400") for title in titles]

    return SimpleNamespace(
        set_titles=set_titles, feed=feed, calls=calls,
        cache=tmp_path / "data/cache/GOOGL-2026-10-30.json",
    )


def test_live_news_skips_placeholders_and_fills_five_slots(live_feed):
    titles = [
        "Alphabet reports revenue growth - Yahoo Finance",
        "AI STOCKS RALLY - Yahoo Finance",
        "GOOGL - Yahoo Finance",
        "Q3_2026 earnings beat expectations - Yahoo Finance",
        "New products expand the market - Yahoo Finance",
        "Sixth eligible headline - Yahoo Finance",
    ]
    live_feed.set_titles([
        "META_TITLE_QUOTE - Yahoo Finance", None, " ",
        titles[0], "META_TITLE_QUOTE", *titles[1:],
    ])
    live_feed.feed["items"].insert(0, ("Old headline", "Thu, 01 Oct 2026 16:00:00 -0400"))
    live_feed.feed["items"].insert(1, ("Future headline", "Sat, 31 Oct 2026 16:00:00 -0400"))

    bundle = data.load_bundle("live", "GOOGL")

    assert [item["title"] for item in bundle["news"]] == titles[:5]
    assert [item["id"] for item in bundle["news"]] == [f"N{i}" for i in range(1, 6)]
    assert all(item["headline_only"] for item in bundle["news"])
    assert json.loads(live_feed.cache.read_text())["news"] == bundle["news"]
    assert any("headlines only" in warning for warning in bundle["warnings"])


@pytest.mark.parametrize("title", [
    None, "", " \t ", " - Yahoo Finance", "META_TITLE_QUOTE",
    " META_TITLE_QUOTE - Yahoo Finance ", "META_TITLE_2026 - Yahoo Finance",
])
def test_live_news_with_no_valid_titles_reports_missing_evidence(live_feed, title):
    live_feed.set_titles([title] * 6)

    bundle = data.load_bundle("live", "GOOGL")

    assert bundle["news"] == []
    assert any("No eligible news" in warning for warning in bundle["warnings"])
    assert not any("headlines only" in warning for warning in bundle["warnings"])


@pytest.mark.parametrize("title", ["META_TITLE_QUOTE - Yahoo Finance", None, " "])
def test_cached_invalid_news_is_refetched(live_feed, title):
    titles = [f"Valid headline {i} - Yahoo Finance" for i in range(6)]
    live_feed.set_titles(titles)
    data.load_bundle("live", "GOOGL")
    cached = json.loads(live_feed.cache.read_text())
    cached["news"][0]["title"] = title
    live_feed.cache.write_text(json.dumps(cached))

    bundle = data.load_bundle("live", "GOOGL")

    assert [item["title"] for item in bundle["news"]] == titles[:5]
    assert live_feed.calls == {"prices": 2, "rss": 2}
    assert json.loads(live_feed.cache.read_text())["news"] == bundle["news"]


def test_valid_news_cache_is_reused_unless_refresh_requested(live_feed):
    live_feed.set_titles(["Alphabet reports revenue growth - Yahoo Finance"])
    original = data.load_bundle("live", "GOOGL")

    cached = data.load_bundle("live", "GOOGL")

    assert cached == original
    assert live_feed.calls == {"prices": 1, "rss": 1}
    live_feed.set_titles(["Alphabet announces a new product - Yahoo Finance"])
    refreshed = data.load_bundle("live", "GOOGL", refresh=True)
    assert refreshed["news"][0]["title"] == "Alphabet announces a new product - Yahoo Finance"
    assert live_feed.calls == {"prices": 2, "rss": 2}
