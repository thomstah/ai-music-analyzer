import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from services.genius import search_song, fetch_lyrics, normalize_lyrics


@pytest.mark.asyncio
async def test_search_song_returns_url_and_id():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": {"hits": [{"result": {"url": "https://genius.com/song", "id": 12345}}]}
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await search_song("Bohemian Rhapsody", "Queen")

    assert result == {"url": "https://genius.com/song", "genius_id": 12345}


@pytest.mark.asyncio
async def test_search_song_raises_404_on_empty_hits():
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": {"hits": []}}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        with pytest.raises(HTTPException) as exc_info:
            await search_song("Nonexistent", "Nobody")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_fetch_lyrics_extracts_text_from_containers():
    html = """
    <html><body>
      <div data-lyrics-container="true">Is this the real life?<br/>Is this just fantasy?</div>
    </body></html>
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = html

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await fetch_lyrics("https://genius.com/song")

    assert "Is this the real life?" in result
    assert "Is this just fantasy?" in result


@pytest.mark.asyncio
async def test_fetch_lyrics_raises_502_when_no_containers():
    html = "<html><body><p>No lyrics here</p></body></html>"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = html

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        with pytest.raises(HTTPException) as exc_info:
            await fetch_lyrics("https://genius.com/song")

    assert exc_info.value.status_code == 502


def test_normalize_lyrics_strips_section_headers():
    raw = "[Verse 1]\nIs this the real life?\n[Chorus]\nEasy come, easy go"
    result = normalize_lyrics(raw)
    assert "[Verse 1]" not in result
    assert "[Chorus]" not in result
    assert "Is this the real life?" in result


def test_normalize_lyrics_collapses_multiple_blank_lines():
    raw = "Line one\n\n\n\nLine two"
    result = normalize_lyrics(raw)
    assert "\n\n\n" not in result
    assert "Line one" in result
    assert "Line two" in result
