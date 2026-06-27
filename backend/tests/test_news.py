import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
import services.news as news_module


def _reset_cache():
    news_module._cache["data"] = None
    news_module._cache["fetched_at"] = None


@pytest.mark.asyncio
async def test_get_music_news_returns_articles():
    _reset_cache()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "ok",
        "articles": [
            {
                "title": "New album drops",
                "description": "It's good",
                "url": "https://pitchfork.com/x",
                "urlToImage": "https://img/x.jpg",
                "source": {"name": "Pitchfork"},
                "publishedAt": "2026-06-25T10:00:00Z",
            }
        ],
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await news_module.get_music_news()

    assert len(result) == 1
    assert result[0]["title"] == "New album drops"
    assert result[0]["source"] == "Pitchfork"


@pytest.mark.asyncio
async def test_get_music_news_returns_cached_on_subsequent_call():
    _reset_cache()
    news_module._cache["data"] = [{"title": "Cached"}]
    news_module._cache["fetched_at"] = datetime.now(timezone.utc)

    with patch("httpx.AsyncClient") as mock_cls:
        result = await news_module.get_music_news()
    mock_cls.assert_not_called()
    assert result[0]["title"] == "Cached"


@pytest.mark.asyncio
async def test_get_music_news_returns_empty_on_error():
    _reset_cache()
    import httpx as _httpx
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=_httpx.RequestError("network down", request=MagicMock())
        )
        result = await news_module.get_music_news()
    assert result == []


@pytest.mark.asyncio
async def test_get_music_news_does_not_cache_empty():
    _reset_cache()
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ok", "articles": []}
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await news_module.get_music_news()
    assert result == []
    assert news_module._cache["data"] is None
