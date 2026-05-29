import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from services.discourse import fetch_discourse, _fetch_reddit, _fetch_genius_annotations

MOCK_REDDIT_SEARCH = {
    "data": {
        "children": [
            {
                "data": {
                    "id": "abc123",
                    "subreddit": "hiphopheads",
                    "subreddit_name_prefixed": "r/hiphopheads",
                    "permalink": "/r/hiphopheads/comments/abc123/passionfruit_drake/",
                }
            }
        ]
    }
}

MOCK_REDDIT_COMMENTS = [
    {"data": {"children": []}},
    {
        "data": {
            "children": [
                {"data": {"body": "This song is about Drake processing his emotions after a complicated relationship."}},
                {"data": {"body": "Short"}},
                {"data": {"body": "Another great comment about the themes in this track and what they mean."}},
                {"data": {"body": "[deleted]"}},
                {"data": {"body": "[removed]"}},
            ]
        }
    },
]

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
async def test_fetch_discourse_combines_reddit_and_genius():
    reddit = [{"source": "reddit", "text": "great analysis", "url": "https://reddit.com/r/x", "metadata": {"subreddit": "r/hiphopheads"}}]
    genius = [{"source": "genius", "text": "deep meaning", "url": None, "metadata": {"lyric_fragment": "sipped lean"}}]

    with patch("services.discourse._fetch_reddit", new_callable=AsyncMock, return_value=reddit), \
         patch("services.discourse._fetch_genius_annotations", new_callable=AsyncMock, return_value=genius):
        result = await fetch_discourse(genius_id=12345, title="Passionfruit", artist="Drake")

    assert len(result) == 2
    assert result[0]["source"] == "reddit"
    assert result[1]["source"] == "genius"


@pytest.mark.asyncio
async def test_fetch_discourse_skips_genius_when_no_genius_id():
    reddit = [{"source": "reddit", "text": "great analysis", "url": "https://reddit.com/r/x", "metadata": {"subreddit": "r/hiphopheads"}}]

    with patch("services.discourse._fetch_reddit", new_callable=AsyncMock, return_value=reddit), \
         patch("services.discourse._fetch_genius_annotations", new_callable=AsyncMock) as mock_genius:
        result = await fetch_discourse(genius_id=None, title="Song", artist="Artist")

    mock_genius.assert_not_called()
    assert all(e["source"] == "reddit" for e in result)


@pytest.mark.asyncio
async def test_fetch_reddit_returns_excerpts():
    mock_cls = _mock_async_client([
        _make_http_response(MOCK_REDDIT_SEARCH),
        _make_http_response(MOCK_REDDIT_COMMENTS),
    ])

    with patch("services.discourse.httpx.AsyncClient", mock_cls):
        result = await _fetch_reddit("Passionfruit", "Drake")

    assert len(result) == 2
    assert result[0]["source"] == "reddit"
    assert result[0]["metadata"]["subreddit"] == "r/hiphopheads"
    assert "reddit.com" in result[0]["url"]


@pytest.mark.asyncio
async def test_fetch_reddit_filters_short_and_deleted_comments():
    mock_cls = _mock_async_client([
        _make_http_response(MOCK_REDDIT_SEARCH),
        _make_http_response(MOCK_REDDIT_COMMENTS),
    ])

    with patch("services.discourse.httpx.AsyncClient", mock_cls):
        result = await _fetch_reddit("Passionfruit", "Drake")

    texts = [e["text"] for e in result]
    assert "Short" not in texts
    assert "[deleted]" not in texts
    assert "[removed]" not in texts


@pytest.mark.asyncio
async def test_fetch_reddit_returns_empty_list_on_error():
    mock_cls = _mock_async_client([Exception("Network error")])

    with patch("services.discourse.httpx.AsyncClient", mock_cls):
        result = await _fetch_reddit("Song", "Artist")

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
