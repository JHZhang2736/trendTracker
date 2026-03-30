"""Tests for GoogleTrendsCollector."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.collectors.google import GoogleTrendsCollector, _parse_traffic
from app.collectors.google_mock import GoogleMockCollector

# ---------------------------------------------------------------------------
# Sample RSS XML fixture
# ---------------------------------------------------------------------------

_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:ht="https://trends.google.com/trending/rss">
  <channel>
    <title>Daily Search Trends</title>
    <item>
      <title>Artificial Intelligence</title>
      <ht:approx_traffic>2,000,000+</ht:approx_traffic>
      <link>https://trends.google.com/trending/rss?geo=US</link>
    </item>
    <item>
      <title>World Cup 2026</title>
      <ht:approx_traffic>1,500,000+</ht:approx_traffic>
      <link>https://trends.google.com/trending/rss?geo=US</link>
    </item>
    <item>
      <title>Stock Market</title>
      <ht:approx_traffic>1,200,000+</ht:approx_traffic>
      <link>https://trends.google.com/trending/rss?geo=US</link>
    </item>
  </channel>
</rss>"""


def _make_mock_response(xml_text: str = _RSS_XML):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.text = xml_text
    return mock_resp


def _patch_httpx(xml_text: str = _RSS_XML):
    mock_resp = _make_mock_response(xml_text)
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)
    return patch("httpx.AsyncClient", return_value=mock_client)


# ---------------------------------------------------------------------------
# Unit tests: _parse_traffic
# ---------------------------------------------------------------------------


def test_parse_traffic_comma_format():
    assert _parse_traffic("1,000,000+") == 1_000_000.0


def test_parse_traffic_k_suffix():
    assert _parse_traffic("500K+") == 500_000.0


def test_parse_traffic_m_suffix():
    assert _parse_traffic("2M+") == 2_000_000.0


def test_parse_traffic_plain_number():
    assert _parse_traffic("50000") == 50_000.0


def test_parse_traffic_invalid_returns_zero():
    assert _parse_traffic("N/A") == 0.0


def test_parse_traffic_empty_returns_zero():
    assert _parse_traffic("") == 0.0


# ---------------------------------------------------------------------------
# Unit tests: GoogleTrendsCollector.collect (mocked HTTP)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_returns_list():
    with _patch_httpx():
        results = await GoogleTrendsCollector().collect()
    assert isinstance(results, list)
    assert len(results) > 0


@pytest.mark.asyncio
async def test_collect_platform_is_google():
    with _patch_httpx():
        results = await GoogleTrendsCollector().collect()
    assert all(r["platform"] == "google" for r in results)


@pytest.mark.asyncio
async def test_collect_item_schema():
    with _patch_httpx():
        results = await GoogleTrendsCollector().collect()
    required = {"platform", "keyword", "rank", "heat_score", "url", "collected_at"}
    for item in results:
        assert required <= set(item.keys())


@pytest.mark.asyncio
async def test_collect_keyword_matches_title():
    with _patch_httpx():
        results = await GoogleTrendsCollector().collect()
    keywords = [r["keyword"] for r in results]
    assert "Artificial Intelligence" in keywords
    assert "World Cup 2026" in keywords


@pytest.mark.asyncio
async def test_collect_heat_score_parsed_correctly():
    with _patch_httpx():
        results = await GoogleTrendsCollector().collect()
    top = next(r for r in results if r["keyword"] == "Artificial Intelligence")
    assert top["heat_score"] == 2_000_000.0


@pytest.mark.asyncio
async def test_collect_rank_is_zero_based():
    with _patch_httpx():
        results = await GoogleTrendsCollector().collect()
    assert results[0]["rank"] == 0
    assert results[1]["rank"] == 1


@pytest.mark.asyncio
async def test_collect_collected_at_is_datetime():
    with _patch_httpx():
        results = await GoogleTrendsCollector().collect()
    for r in results:
        assert isinstance(r["collected_at"], datetime)


@pytest.mark.asyncio
async def test_collect_truncates_at_20():
    # Build RSS with 25 items
    items_xml = "\n".join(
        f"<item><title>Term{i}</title>"
        f"<ht:approx_traffic>100,000+</ht:approx_traffic>"
        f"<link>https://example.com/{i}</link></item>"
        for i in range(25)
    )
    big_rss = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0" xmlns:ht="https://trends.google.com/trending/rss">'
        f"<channel>{items_xml}</channel></rss>"
    )
    with _patch_httpx(big_rss):
        results = await GoogleTrendsCollector().collect()
    assert len(results) <= 20


@pytest.mark.asyncio
async def test_collect_custom_geos():
    collector = GoogleTrendsCollector(geos=("TW", "JP"))
    captured_urls: list[str] = []

    mock_resp = _make_mock_response()
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    async def fake_get(url, **kwargs):
        captured_urls.append(url)
        return mock_resp

    mock_client.get = fake_get
    with patch("httpx.AsyncClient", return_value=mock_client):
        await collector.collect()

    assert len(captured_urls) == 2
    assert any("geo=TW" in u for u in captured_urls)
    assert any("geo=JP" in u for u in captured_urls)


# ---------------------------------------------------------------------------
# Unit tests: GoogleMockCollector
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_collector_returns_list():
    results = await GoogleMockCollector().collect()
    assert isinstance(results, list)
    assert len(results) > 0


@pytest.mark.asyncio
async def test_mock_collector_platform_is_google():
    results = await GoogleMockCollector().collect()
    assert all(r["platform"] == "google" for r in results)


@pytest.mark.asyncio
async def test_mock_collector_no_network():
    # Must not raise even without network
    results = await GoogleMockCollector().collect()
    assert len(results) == 5


# ---------------------------------------------------------------------------
# Integration: registry picks up DailyHot platforms (Google removed)
# ---------------------------------------------------------------------------


def test_dailyhot_platforms_registered_in_registry():
    from app.collectors.registry import registry

    platforms = registry.list_platforms()
    assert "zhihu" in platforms
    assert "bilibili" in platforms
    assert "douyin" in platforms
