import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta
import services.billboard as billboard_module


def _reset_cache():
    billboard_module._cache["data"] = None
    billboard_module._cache["fetched_at"] = None


@pytest.mark.asyncio
async def test_get_hot_100_returns_enriched_results_and_caches():
    _reset_cache()
    fake_entry = MagicMock(title="Test Song", artist="Test Artist")
    fake_chart = MagicMock()
    fake_chart.__getitem__ = lambda self, key: [fake_entry] if isinstance(key, slice) else fake_entry

    with patch("billboard.ChartData", return_value=fake_chart), \
         patch("services.billboard.deezer_service.search_track_cover",
               new_callable=AsyncMock, return_value="https://img/cover.jpg"):
        result = await billboard_module.get_hot_100(10)
    assert result == [{"rank": 1, "title": "Test Song", "artist": "Test Artist", "cover_url": "https://img/cover.jpg"}]
    assert billboard_module._cache["data"] == result


@pytest.mark.asyncio
async def test_get_hot_100_returns_cached_on_subsequent_call():
    _reset_cache()
    billboard_module._cache["data"] = [{"rank": 1, "title": "Cached", "artist": "Cached", "cover_url": None}]
    billboard_module._cache["fetched_at"] = datetime.now(timezone.utc)

    with patch("billboard.ChartData") as mock_chart, \
         patch("services.billboard.deezer_service.search_track_cover", new_callable=AsyncMock) as mock_deezer:
        result = await billboard_module.get_hot_100(10)
    mock_chart.assert_not_called()
    mock_deezer.assert_not_called()
    assert result[0]["title"] == "Cached"


@pytest.mark.asyncio
async def test_get_hot_100_falls_back_to_stale_cache_on_error():
    _reset_cache()
    billboard_module._cache["data"] = [{"rank": 1, "title": "Stale", "artist": "Stale", "cover_url": None}]
    billboard_module._cache["fetched_at"] = datetime.now(timezone.utc) - timedelta(days=2)

    with patch("billboard.ChartData", side_effect=Exception("network error")):
        result = await billboard_module.get_hot_100(10)
    assert result[0]["title"] == "Stale"


@pytest.mark.asyncio
async def test_get_hot_100_does_not_cache_empty_results():
    _reset_cache()
    fake_chart = MagicMock()
    fake_chart.__getitem__ = lambda self, key: []

    with patch("billboard.ChartData", return_value=fake_chart), \
         patch("services.billboard.deezer_service.search_track_cover", new_callable=AsyncMock, return_value=None):
        result = await billboard_module.get_hot_100(10)
    assert result == []
    assert billboard_module._cache["data"] is None


@pytest.mark.asyncio
async def test_get_hot_100_handles_missing_cover_gracefully():
    _reset_cache()
    fake_entry = MagicMock(title="No Match", artist="Unknown")
    fake_chart = MagicMock()
    fake_chart.__getitem__ = lambda self, key: [fake_entry] if isinstance(key, slice) else fake_entry

    with patch("billboard.ChartData", return_value=fake_chart), \
         patch("services.billboard.deezer_service.search_track_cover",
               new_callable=AsyncMock, return_value=None):
        result = await billboard_module.get_hot_100(10)
    assert result[0]["cover_url"] is None
