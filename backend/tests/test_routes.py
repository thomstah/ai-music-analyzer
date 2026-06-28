import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from main import app
from models.schemas import DiscourseExcerpt, SongResponse

client = TestClient(app)

MOCK_DISCOURSE_EXCERPTS = [
    {
        "source": "reddit",
        "text": "This song is about Drake processing his emotions.",
        "url": "https://reddit.com/r/hiphopheads/comments/abc",
        "metadata": {"subreddit": "r/hiphopheads"},
    }
]


def _fresh_scraped_at():
    return datetime.now(timezone.utc).isoformat()


def _stale_scraped_at():
    return (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()


def test_discourse_excerpt_schema_validates():
    exc = DiscourseExcerpt(
        source="reddit",
        text="This is a great analysis of the song.",
        url="https://reddit.com/r/hiphopheads/comments/abc",
        metadata={"subreddit": "r/hiphopheads"},
    )
    assert exc.source == "reddit"
    assert exc.text == "This is a great analysis of the song."
    assert exc.url == "https://reddit.com/r/hiphopheads/comments/abc"
    assert exc.metadata == {"subreddit": "r/hiphopheads"}

    # url defaults to None when omitted
    exc_no_url = DiscourseExcerpt(source="genius", text="annotation", metadata={"lyric_fragment": "lean"})
    assert exc_no_url.url is None


def test_song_response_accepts_community_commentary():
    exc = DiscourseExcerpt(source="genius", text="annotation", url=None, metadata={"lyric_fragment": "lean"})
    resp = SongResponse(
        id="1", title="Song", artist="Artist", lyrics="words", community_commentary=[exc]
    )
    assert len(resp.community_commentary) == 1
    assert resp.community_commentary[0].source == "genius"


MOCK_INTERPRETATION = {
    "tldr": "A song about the meaning of life.",
    "overall_meaning": "A song about life.",
    "emotional_tone": "hopeful",
    "themes": ["life", "hope"],
    "key_lyric_breakdowns": [{"lyric": "Is this the real life?", "breakdown": "Questions reality."}],
}

MOCK_SONG_FROM_DB = {
    "id": "song-123",
    "title": "Bohemian Rhapsody",
    "artist": "Queen",
    "lyrics": "Is this the real life?",
    "genius_id": 12345,
    "created_at": "2026-05-17T00:00:00",
    "interpretations": [{"content": MOCK_INTERPRETATION, "model_version": "claude-sonnet-4-6"}],
}


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_returns_cached_result_when_song_exists():
    fresh_row = {"id": "disc-1", "song_id": "song-123", "excerpts": [], "scraped_at": _fresh_scraped_at()}
    with patch("routes.songs.supabase_service.find_song", return_value=MOCK_SONG_FROM_DB), \
         patch("routes.songs.supabase_service.find_discourse", return_value=fresh_row):
        response = client.post("/analyze", json={"title": "Bohemian Rhapsody", "artist": "Queen"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "song-123"
    assert data["interpretation"]["emotional_tone"] == "hopeful"
    assert "community_commentary" in data


def test_analyze_runs_full_flow_when_not_cached():
    stored_song = {
        "id": "new-song-id",
        "title": "Bohemian Rhapsody",
        "artist": "Queen",
        "lyrics": "lyrics text",
        "genius_id": 12345,
        "created_at": "2026-05-17T00:00:00",
    }
    with patch("routes.songs.supabase_service.find_song", return_value=None), \
         patch("routes.songs.genius_service.search_song", new_callable=AsyncMock,
               return_value={"url": "https://genius.com/song", "genius_id": 12345}), \
         patch("routes.songs.genius_service.get_song_details", new_callable=AsyncMock,
               return_value={"album_art_url": None, "album_name": None, "release_year": None, "producer": None}), \
         patch("routes.songs.genius_service.fetch_lyrics", new_callable=AsyncMock,
               return_value="lyrics text"), \
         patch("routes.songs.discourse_service.fetch_discourse", new_callable=AsyncMock,
               return_value=[]), \
         patch("routes.songs.anthropic_service.generate_interpretation", new_callable=AsyncMock,
               return_value=(MOCK_INTERPRETATION, "claude-sonnet-4-6")), \
         patch("routes.songs.supabase_service.store_song", return_value=stored_song), \
         patch("routes.songs.supabase_service.store_interpretation", return_value={}), \
         patch("routes.songs.supabase_service.store_discourse", return_value={}):
        response = client.post("/analyze", json={"title": "Bohemian Rhapsody", "artist": "Queen"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "new-song-id"
    assert data["interpretation"]["emotional_tone"] == "hopeful"


def test_songs_search_returns_categorized_results():
    categorized = {
        "songs": [{"title": "Bohemian Rhapsody", "artist": "Queen", "genius_id": 1, "thumbnail": None}],
        "lyrics": [],
        "artists": [{"name": "Queen", "artist_id": 42, "thumbnail": None}],
    }
    with patch("routes.songs.genius_service.search_songs", return_value=categorized), \
         patch("routes.songs.supabase_service.search_cached_albums", return_value=[]):
        response = client.get("/songs/search?q=queen")
    assert response.status_code == 200
    data = response.json()
    assert data["songs"][0]["title"] == "Bohemian Rhapsody"
    assert data["artists"][0]["name"] == "Queen"
    assert data["lyrics"] == []
    assert data["albums"] == []


def test_songs_search_returns_empty_categories_when_no_results():
    empty = {"songs": [], "lyrics": [], "artists": []}
    with patch("routes.songs.genius_service.search_songs", return_value=empty), \
         patch("routes.songs.supabase_service.search_cached_albums", return_value=[]):
        response = client.get("/songs/search?q=xyznotareal")
    assert response.status_code == 200
    assert response.json() == {"songs": [], "lyrics": [], "artists": [], "albums": []}


def test_songs_search_includes_albums_from_cache():
    genius_results = {"songs": [], "lyrics": [], "artists": []}
    albums = [{"album_id": 100, "name": "Album", "artist": "Artist", "thumbnail": None}]
    with patch("routes.songs.genius_service.search_songs", return_value=genius_results), \
         patch("routes.songs.supabase_service.search_cached_albums", return_value=albums):
        response = client.get("/songs/search?q=test")
    assert response.status_code == 200
    data = response.json()
    assert data["albums"][0]["name"] == "Album"


def test_songs_search_requires_q_param():
    response = client.get("/songs/search")
    assert response.status_code == 422


def test_get_song_by_id_returns_404_when_not_found():
    with patch("routes.songs.supabase_service.get_song_by_id", return_value=None):
        response = client.get("/song/nonexistent-id")
    assert response.status_code == 404


def test_get_song_by_id_returns_song_when_found():
    with patch("routes.songs.supabase_service.get_song_by_id", return_value=MOCK_SONG_FROM_DB):
        response = client.get("/song/song-123")
    assert response.status_code == 200
    assert response.json()["id"] == "song-123"


def test_analyze_returns_community_commentary_on_new_song():
    stored_song = {
        "id": "new-song-id",
        "title": "Passionfruit",
        "artist": "Drake",
        "lyrics": "lyrics text",
        "genius_id": 12345,
        "created_at": "2026-05-29T00:00:00",
    }
    with patch("routes.songs.supabase_service.find_song", return_value=None), \
         patch("routes.songs.genius_service.search_song", new_callable=AsyncMock,
               return_value={"url": "https://genius.com/song", "genius_id": 12345}), \
         patch("routes.songs.genius_service.get_song_details", new_callable=AsyncMock,
               return_value={"album_art_url": None, "album_name": None, "release_year": None, "producer": None}), \
         patch("routes.songs.genius_service.fetch_lyrics", new_callable=AsyncMock,
               return_value="lyrics text"), \
         patch("routes.songs.discourse_service.fetch_discourse", new_callable=AsyncMock,
               return_value=MOCK_DISCOURSE_EXCERPTS), \
         patch("routes.songs.anthropic_service.generate_interpretation", new_callable=AsyncMock,
               return_value=(MOCK_INTERPRETATION, "claude-sonnet-4-6")), \
         patch("routes.songs.supabase_service.store_song", return_value=stored_song), \
         patch("routes.songs.supabase_service.store_interpretation", return_value={}), \
         patch("routes.songs.supabase_service.store_discourse", return_value={}):
        response = client.post("/analyze", json={"title": "Passionfruit", "artist": "Drake"})

    assert response.status_code == 200
    data = response.json()
    assert len(data["community_commentary"]) == 1
    assert data["community_commentary"][0]["source"] == "reddit"


def test_analyze_returns_fresh_cached_discourse_for_cached_song():
    fresh_row = {"id": "disc-1", "song_id": "song-123", "excerpts": MOCK_DISCOURSE_EXCERPTS, "scraped_at": _fresh_scraped_at()}
    with patch("routes.songs.supabase_service.find_song", return_value=MOCK_SONG_FROM_DB), \
         patch("routes.songs.supabase_service.find_discourse", return_value=fresh_row), \
         patch("routes.songs.discourse_service.fetch_discourse", new_callable=AsyncMock) as mock_fetch:
        response = client.post("/analyze", json={"title": "Bohemian Rhapsody", "artist": "Queen"})

    assert response.status_code == 200
    mock_fetch.assert_not_called()
    data = response.json()
    assert data["community_commentary"][0]["source"] == "reddit"


def test_analyze_refreshes_stale_discourse_for_cached_song():
    stale_row = {"id": "disc-1", "song_id": "song-123", "excerpts": [], "scraped_at": _stale_scraped_at()}
    with patch("routes.songs.supabase_service.find_song", return_value=MOCK_SONG_FROM_DB), \
         patch("routes.songs.supabase_service.find_discourse", return_value=stale_row), \
         patch("routes.songs.discourse_service.fetch_discourse", new_callable=AsyncMock,
               return_value=MOCK_DISCOURSE_EXCERPTS) as mock_fetch, \
         patch("routes.songs.supabase_service.store_discourse", return_value={}):
        response = client.post("/analyze", json={"title": "Bohemian Rhapsody", "artist": "Queen"})

    assert response.status_code == 200
    mock_fetch.assert_called_once()
    data = response.json()
    assert data["community_commentary"][0]["source"] == "reddit"


def test_analyze_scrapes_discourse_when_none_cached_for_cached_song():
    with patch("routes.songs.supabase_service.find_song", return_value=MOCK_SONG_FROM_DB), \
         patch("routes.songs.supabase_service.find_discourse", return_value=None), \
         patch("routes.songs.discourse_service.fetch_discourse", new_callable=AsyncMock,
               return_value=MOCK_DISCOURSE_EXCERPTS), \
         patch("routes.songs.supabase_service.store_discourse", return_value={}):
        response = client.post("/analyze", json={"title": "Bohemian Rhapsody", "artist": "Queen"})

    assert response.status_code == 200
    data = response.json()
    assert data["community_commentary"][0]["source"] == "reddit"


def test_trending_returns_songs():
    songs = [{"id": "a", "title": "Hit Song", "artist": "Artist", "request_count": 100}]
    with patch("routes.songs.supabase_service.get_trending", return_value=songs):
        response = client.get("/songs/trending?limit=10")
    assert response.status_code == 200
    assert response.json()[0]["request_count"] == 100


def test_trending_returns_empty_list_when_no_songs():
    with patch("routes.songs.supabase_service.get_trending", return_value=[]):
        response = client.get("/songs/trending")
    assert response.status_code == 200
    assert response.json() == []


def test_trending_rejects_limit_below_minimum():
    response = client.get("/songs/trending?limit=0")
    assert response.status_code == 422


def test_trending_rejects_limit_above_maximum():
    response = client.get("/songs/trending?limit=51")
    assert response.status_code == 422


def test_billboard_returns_top_songs():
    songs = [{"rank": 1, "title": "Not Like Us", "artist": "Kendrick Lamar"}]
    with patch("routes.songs.billboard_service.get_hot_100", return_value=songs):
        response = client.get("/songs/billboard")
    assert response.status_code == 200
    assert response.json()[0]["rank"] == 1
    assert response.json()[0]["title"] == "Not Like Us"


def test_billboard_returns_empty_list_on_failure():
    with patch("routes.songs.billboard_service.get_hot_100", return_value=[]):
        response = client.get("/songs/billboard")
    assert response.status_code == 200
    assert response.json() == []


def test_news_returns_articles():
    articles = [{"title": "Test", "description": "x", "url": "u", "image_url": None, "source": "S", "published_at": "2026-01-01"}]
    with patch("routes.songs.news_service.get_music_news", new_callable=AsyncMock, return_value=articles):
        response = client.get("/news")
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Test"


def test_trending_themes_returns_aggregated_counts():
    themes_data = [{"theme": "love", "count": 12}, {"theme": "loss", "count": 7}]
    with patch("routes.songs.supabase_service.get_trending_themes", return_value=themes_data):
        response = client.get("/trending/themes?limit=5")
    assert response.status_code == 200
    assert response.json()[0]["theme"] == "love"
    assert response.json()[0]["count"] == 12


def test_trending_themes_empty_when_no_data():
    with patch("routes.songs.supabase_service.get_trending_themes", return_value=[]):
        response = client.get("/trending/themes")
    assert response.status_code == 200
    assert response.json() == []


def test_songs_search_handles_query_with_special_chars():
    # Query with commas/quotes/parens should not blow up the SQL filter
    with patch("routes.songs.genius_service.search_songs", return_value={"songs": [], "lyrics": [], "artists": []}), \
         patch("routes.songs.supabase_service.search_cached_albums", return_value=[]):
        response = client.get("/songs/search?q=foo%2Cbar%22baz")  # foo,bar"baz
    assert response.status_code == 200


MOCK_ALBUM = {
    "id": "album-uuid-1",
    "genius_id": 100,
    "title": "Album Name",
    "artist": "Artist",
    "release_year": "2024",
    "cover_art_url": "https://images.genius.com/x.jpg",
    "producers": ["Producer One", "Producer Two"],
    "tracklist": [{"genius_id": 1, "title": "Track 1", "thumbnail": None}],
}


def test_get_album_returns_cached_album_by_genius_id():
    with patch("routes.songs.supabase_service.get_album_by_id", return_value=None), \
         patch("routes.songs.supabase_service.find_album", return_value=MOCK_ALBUM):
        response = client.get("/album/100")
    assert response.status_code == 200
    assert response.json()["title"] == "Album Name"


def test_get_album_fetches_from_genius_when_not_cached():
    fetched = {
        "genius_id": 100, "title": "New Album", "artist": "A",
        "release_year": "2024", "cover_art_url": None,
        "producers": [], "tracklist": [],
    }
    with patch("routes.songs.supabase_service.get_album_by_id", return_value=None), \
         patch("routes.songs.supabase_service.find_album", return_value=None), \
         patch("routes.songs.genius_service.get_album_details", new_callable=AsyncMock, return_value=fetched), \
         patch("routes.songs.supabase_service.store_album", return_value={**MOCK_ALBUM, "title": "New Album"}):
        response = client.get("/album/100")
    assert response.status_code == 200
    assert response.json()["title"] == "New Album"


def test_get_album_returns_404_when_not_found_anywhere():
    with patch("routes.songs.supabase_service.get_album_by_id", return_value=None), \
         patch("routes.songs.supabase_service.find_album", return_value=None), \
         patch("routes.songs.genius_service.get_album_details", new_callable=AsyncMock, return_value={}):
        response = client.get("/album/100")
    assert response.status_code == 404


def test_get_album_integer_id_skips_uuid_lookup():
    # Bug fix: a numeric album_id like "915226" must NOT be passed to get_album_by_id
    # (which queries a UUID column and would raise 22P02 in Postgres).
    with patch("routes.songs.supabase_service.get_album_by_id") as mock_uuid_lookup, \
         patch("routes.songs.supabase_service.find_album", return_value=MOCK_ALBUM):
        response = client.get("/album/915226")
    assert response.status_code == 200
    mock_uuid_lookup.assert_not_called()


def test_get_album_uuid_id_does_not_call_find_album():
    # A UUID-shaped id should route to get_album_by_id only.
    with patch("routes.songs.supabase_service.get_album_by_id", return_value=MOCK_ALBUM), \
         patch("routes.songs.supabase_service.find_album") as mock_genius_cache:
        response = client.get("/album/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    assert response.status_code == 200
    mock_genius_cache.assert_not_called()
