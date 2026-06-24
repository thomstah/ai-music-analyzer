import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from services.genius import search_song, fetch_lyrics, normalize_lyrics, get_song_details, search_songs


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
async def test_search_song_raises_502_on_api_error():
    import httpx as _httpx
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(
            side_effect=_httpx.HTTPStatusError(
                "500 Server Error", request=MagicMock(), response=MagicMock()
            )
        )
        with pytest.raises(HTTPException) as exc_info:
            await search_song("Song", "Artist")
    assert exc_info.value.status_code == 502


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


def test_normalize_lyrics_strips_contributor_and_translation_header():
    # Two lines so each regex is exercised independently
    raw = "67 ContributorsTranslationsFrançaisItaliano\nSlap The City Lyrics\nYeah\nSlap the city"
    result = normalize_lyrics(raw)
    assert "Contributors" not in result
    assert "Français" not in result
    assert "Slap The City Lyrics" not in result
    assert "Yeah" in result
    assert "Slap the city" in result


def test_normalize_lyrics_strips_song_title_lyrics_line():
    raw = "Bohemian Rhapsody Lyrics\nIs this the real life?"
    result = normalize_lyrics(raw)
    assert "Bohemian Rhapsody Lyrics" not in result
    assert "Is this the real life?" in result


def test_normalize_lyrics_preserves_lyric_lines_containing_word_lyrics():
    # Genius header only ever appears at document start. A real lyric line
    # containing "Lyrics" must NOT be stripped.
    raw = "Song Title Lyrics\nI'm writing the Lyrics\nTo a song you'll never sing"
    result = normalize_lyrics(raw)
    # The header (first line) is stripped
    assert "Song Title Lyrics" not in result
    # The legitimate lyric lines survive
    assert "I'm writing the Lyrics" in result
    assert "To a song you'll never sing" in result


@pytest.mark.asyncio
async def test_get_song_details_returns_metadata():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": {
            "song": {
                "song_art_image_url": "https://images.genius.com/art.jpg",
                "album": {"name": "Certified Lover Boy", "release_date_for_display": "September 3, 2021"},
                "producer_artists": [{"name": "Noah '40' Shebib"}],
            }
        }
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await get_song_details(12345)

    assert result["album_art_url"] == "https://images.genius.com/art.jpg"
    assert result["album_name"] == "Certified Lover Boy"
    assert result["release_year"] == "2021"
    assert result["producer"] == "Noah '40' Shebib"


@pytest.mark.asyncio
async def test_get_song_details_returns_empty_dict_on_error():
    import httpx as _httpx
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(
            side_effect=_httpx.HTTPStatusError(
                "500 Server Error", request=MagicMock(), response=MagicMock()
            )
        )
        result = await get_song_details(12345)
    assert result == {}


@pytest.mark.asyncio
async def test_get_song_details_returns_none_year_for_non_date_garbage():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": {
            "song": {
                "song_art_image_url": None,
                "album": {"name": "Album", "release_date_for_display": "TBA"},
                "producer_artists": [],
            }
        }
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await get_song_details(12345)

    assert result["release_year"] is None


@pytest.mark.asyncio
async def test_search_songs_filters_out_genius_translation_accounts():
    hits = [
        {
            "type": "song",
            "result": {
                "id": 1,
                "title": "Slap The City",
                "primary_artist": {"id": 100, "name": "Drake"},
                "song_art_image_thumbnail_url": None,
            },
        },
        {
            "type": "song",
            "result": {
                "id": 2,
                "title": "Slap The City (Tradução em Português)",
                "primary_artist": {"id": 200, "name": "Genius Brasil Traduções"},
                "song_art_image_thumbnail_url": None,
            },
        },
        {
            "type": "song",
            "result": {
                "id": 3,
                "title": "Slap The City (Türkçe Çeviri)",
                "primary_artist": {"id": 300, "name": "Genius Türkçe Çeviriler"},
                "song_art_image_thumbnail_url": None,
            },
        },
    ]
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": {"hits": hits}}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await search_songs("slap the city")

    titles = [s["title"] for s in result["songs"]]
    assert "Slap The City" in titles
    assert all("Tradução" not in t and "Çeviri" not in t for t in titles)
    assert len(result["songs"]) == 1
