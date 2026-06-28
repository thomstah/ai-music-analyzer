import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import services.deezer as deezer


@pytest.mark.asyncio
async def test_search_artist_by_name_returns_first_match():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"id": 246791, "name": "Drake", "picture_xl": "https://img/x.jpg"}
        ]
    }
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await deezer.search_artist_by_name("Drake")
    assert result == {"id": 246791, "name": "Drake", "picture_xl": "https://img/x.jpg"}


@pytest.mark.asyncio
async def test_search_artist_by_name_returns_none_when_empty():
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": []}
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await deezer.search_artist_by_name("xyz nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_get_artist_albums_filters_to_full_albums_and_dedupes():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"id": 1, "title": "Album One", "cover_xl": "u1", "release_date": "2024-01-15", "record_type": "album", "fans": 100},
            {"id": 2, "title": "Album One (Deluxe)", "cover_xl": "u2", "release_date": "2024-02-15", "record_type": "album", "fans": 50},
            {"id": 3, "title": "Single Track", "cover_xl": "u3", "release_date": "2023-11-15", "record_type": "single", "fans": 200},
        ]
    }
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        albums = await deezer.get_artist_albums(246791, limit=10)
    # Singles excluded; both Album One variants kept (different IDs, full albums)
    assert len(albums) == 2
    assert albums[0]["title"] == "Album One"
    assert albums[0]["cover_url"] == "u1"
    assert albums[0]["release_year"] == "2024"


@pytest.mark.asyncio
async def test_get_artist_albums_returns_empty_on_error():
    import httpx as _httpx
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=_httpx.RequestError("network", request=MagicMock())
        )
        result = await deezer.get_artist_albums(123)
    assert result == []
