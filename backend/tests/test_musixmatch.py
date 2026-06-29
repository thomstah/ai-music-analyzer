import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import services.musixmatch as mxm


@pytest.mark.asyncio
async def test_search_track_returns_first_match():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {
            "body": {
                "track_list": [
                    {"track": {"track_id": 12345, "track_name": "Test", "track_share_url": "https://mxm/x"}}
                ]
            }
        }
    }
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await mxm.search_track("Test", "Artist")
    assert result["track_id"] == 12345


@pytest.mark.asyncio
async def test_search_track_returns_none_when_empty():
    mock_response = MagicMock()
    mock_response.json.return_value = {"message": {"body": {"track_list": []}}}
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await mxm.search_track("xyz", "nobody")
    assert result is None


@pytest.mark.asyncio
async def test_get_lyrics_strips_tracking_footer():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {
            "body": {
                "lyrics": {
                    "lyrics_body": "Verse one\nVerse two\n\n******* This Lyrics is NOT for Commercial use *******\n(1409617533666)",
                    "pixel_tracking_url": "https://tracking/pixel",
                }
            }
        }
    }
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await mxm.get_lyrics(12345)
    assert result["lyrics"] == "Verse one\nVerse two"
    assert "*******" not in result["lyrics"]
    assert result["pixel_tracking_url"] == "https://tracking/pixel"


@pytest.mark.asyncio
async def test_get_lyrics_returns_none_when_empty():
    mock_response = MagicMock()
    mock_response.json.return_value = {"message": {"body": {"lyrics": {"lyrics_body": ""}}}}
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await mxm.get_lyrics(12345)
    assert result is None


@pytest.mark.asyncio
async def test_fetch_lyrics_by_name_combines_search_and_lyrics():
    search_resp = MagicMock()
    search_resp.json.return_value = {
        "message": {"body": {"track_list": [{"track": {"track_id": 12345, "track_share_url": "https://mxm/x"}}]}}
    }
    search_resp.raise_for_status = MagicMock()

    lyrics_resp = MagicMock()
    lyrics_resp.json.return_value = {
        "message": {"body": {"lyrics": {"lyrics_body": "Hello world", "pixel_tracking_url": None}}}
    }
    lyrics_resp.raise_for_status = MagicMock()

    call_order = []

    async def fake_get(url, **kwargs):
        call_order.append(url)
        return search_resp if "search" in url else lyrics_resp

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(side_effect=fake_get)
        result = await mxm.fetch_lyrics_by_name("Test", "Artist")
    assert result["lyrics"] == "Hello world"
    assert result["track_share_url"] == "https://mxm/x"
    assert result["musixmatch_track_id"] == 12345


@pytest.mark.asyncio
async def test_search_track_returns_none_on_error():
    import httpx as _httpx
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=_httpx.RequestError("network", request=MagicMock())
        )
        result = await mxm.search_track("Test", "Artist")
    assert result is None
