import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from services.discourse import fetch_discourse, _fetch_youtube_comments, _fetch_genius_annotations

MOCK_YOUTUBE_SEARCH = {
    "items": [
        {
            "id": {"videoId": "abc123"},
            "snippet": {"title": "Passionfruit - Drake (Official Video)"},
        }
    ]
}

MOCK_YOUTUBE_COMMENTS = {
    "items": [
        {
            "snippet": {
                "topLevelComment": {
                    "snippet": {
                        "textDisplay": "This song is about Drake processing his emotions after a complicated relationship with someone abroad."
                    }
                }
            }
        },
        {
            "snippet": {
                "topLevelComment": {
                    "snippet": {"textDisplay": "Short"}
                }
            }
        },
        {
            "snippet": {
                "topLevelComment": {
                    "snippet": {
                        "textDisplay": "The tropical house production perfectly mirrors the longing and distance described in the lyrics."
                    }
                }
            }
        },
    ]
}

MOCK_GENIUS_REFERENTS = {
    "response": {
        "referents": [
            {
                "fragment": "I sipped lean and lost my mind",
                "annotations": [
                    {"body": {"plain": "A reference to the Houston lean culture that Drake adopted through his OVO connections."}}
                ],
            },
            {
                "fragment": "Short",
                "annotations": [{"body": {"plain": "Hi"}}],
            },
        ]
    }
}


def _make_http_response(json_data):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = json_data
    return resp


def _mock_async_client(responses):
    mock_cls = MagicMock()
    mock_instance = MagicMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
    mock_instance.get = AsyncMock(side_effect=responses)
    return mock_cls


@pytest.mark.asyncio
async def test_fetch_discourse_combines_youtube_and_genius():
    youtube = [{"source": "youtube", "text": "great analysis", "url": "https://youtube.com/watch?v=x", "metadata": {"video_title": "Passionfruit"}}]
    genius = [{"source": "genius", "text": "deep meaning", "url": None, "metadata": {"lyric_fragment": "sipped lean"}}]

    with patch("services.discourse._fetch_youtube_comments", new_callable=AsyncMock, return_value=youtube), \
         patch("services.discourse._fetch_genius_annotations", new_callable=AsyncMock, return_value=genius):
        result = await fetch_discourse(genius_id=12345, title="Passionfruit", artist="Drake")

    assert len(result) == 2
    assert result[0]["source"] == "genius"
    assert result[1]["source"] == "youtube"


@pytest.mark.asyncio
async def test_fetch_discourse_skips_genius_when_no_genius_id():
    youtube = [{"source": "youtube", "text": "great analysis", "url": "https://youtube.com/watch?v=x", "metadata": {"video_title": "Song"}}]

    with patch("services.discourse._fetch_youtube_comments", new_callable=AsyncMock, return_value=youtube), \
         patch("services.discourse._fetch_genius_annotations", new_callable=AsyncMock) as mock_genius:
        result = await fetch_discourse(genius_id=None, title="Song", artist="Artist")

    mock_genius.assert_not_called()
    assert all(e["source"] == "youtube" for e in result)


@pytest.mark.asyncio
async def test_fetch_youtube_comments_returns_excerpts():
    mock_cls = _mock_async_client([
        _make_http_response(MOCK_YOUTUBE_SEARCH),
        _make_http_response(MOCK_YOUTUBE_COMMENTS),
    ])

    with patch("services.discourse.httpx.AsyncClient", mock_cls):
        result = await _fetch_youtube_comments("Passionfruit", "Drake")

    assert len(result) == 2
    assert result[0]["source"] == "youtube"
    assert result[0]["metadata"]["video_title"] == "Passionfruit - Drake (Official Video)"
    assert "youtube.com/watch?v=abc123" in result[0]["url"]


@pytest.mark.asyncio
async def test_fetch_youtube_comments_filters_short_comments():
    mock_cls = _mock_async_client([
        _make_http_response(MOCK_YOUTUBE_SEARCH),
        _make_http_response(MOCK_YOUTUBE_COMMENTS),
    ])

    with patch("services.discourse.httpx.AsyncClient", mock_cls):
        result = await _fetch_youtube_comments("Passionfruit", "Drake")

    texts = [e["text"] for e in result]
    assert "Short" not in texts


@pytest.mark.asyncio
async def test_fetch_youtube_comments_returns_empty_when_no_videos():
    empty_search = {"items": []}
    mock_cls = _mock_async_client([_make_http_response(empty_search)])

    with patch("services.discourse.httpx.AsyncClient", mock_cls):
        result = await _fetch_youtube_comments("Unknown Song", "Unknown Artist")

    assert result == []


@pytest.mark.asyncio
async def test_fetch_youtube_comments_returns_empty_list_on_error():
    mock_cls = _mock_async_client([Exception("Network error")])

    with patch("services.discourse.httpx.AsyncClient", mock_cls):
        result = await _fetch_youtube_comments("Song", "Artist")

    assert result == []


@pytest.mark.asyncio
async def test_fetch_genius_annotations_returns_excerpts():
    mock_cls = _mock_async_client([_make_http_response(MOCK_GENIUS_REFERENTS)])

    with patch("services.discourse.httpx.AsyncClient", mock_cls):
        result = await _fetch_genius_annotations(12345)

    assert len(result) == 2
    assert result[0]["source"] == "genius"
    assert result[0]["metadata"]["lyric_fragment"] == "I sipped lean and lost my mind"


@pytest.mark.asyncio
async def test_fetch_genius_annotations_returns_empty_list_on_error():
    mock_cls = _mock_async_client([Exception("API error")])

    with patch("services.discourse.httpx.AsyncClient", mock_cls):
        result = await _fetch_genius_annotations(12345)

    assert result == []
