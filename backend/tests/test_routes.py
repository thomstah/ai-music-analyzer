import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

MOCK_INTERPRETATION = {
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
    with patch("routes.songs.supabase_service.find_song", return_value=MOCK_SONG_FROM_DB):
        response = client.post("/analyze", json={"title": "Bohemian Rhapsody", "artist": "Queen"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "song-123"
    assert data["interpretation"]["emotional_tone"] == "hopeful"


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
         patch("routes.songs.genius_service.fetch_lyrics", new_callable=AsyncMock,
               return_value="lyrics text"), \
         patch("routes.songs.anthropic_service.generate_interpretation", new_callable=AsyncMock,
               return_value=(MOCK_INTERPRETATION, "claude-sonnet-4-6")), \
         patch("routes.songs.supabase_service.store_song", return_value=stored_song), \
         patch("routes.songs.supabase_service.store_interpretation", return_value={}):
        response = client.post("/analyze", json={"title": "Bohemian Rhapsody", "artist": "Queen"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "new-song-id"
    assert data["interpretation"]["emotional_tone"] == "hopeful"


def test_songs_search_returns_not_found_when_no_match():
    with patch("routes.songs.supabase_service.find_song", return_value=None):
        response = client.get("/songs/search?title=Unknown&artist=Nobody")
    assert response.status_code == 200
    assert response.json() == {"found": False, "song": None}


def test_songs_search_returns_song_when_found():
    with patch("routes.songs.supabase_service.find_song", return_value=MOCK_SONG_FROM_DB):
        response = client.get("/songs/search?title=Bohemian+Rhapsody&artist=Queen")
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert data["song"]["id"] == "song-123"


def test_get_song_by_id_returns_404_when_not_found():
    with patch("routes.songs.supabase_service.get_song_by_id", return_value=None):
        response = client.get("/song/nonexistent-id")
    assert response.status_code == 404


def test_get_song_by_id_returns_song_when_found():
    with patch("routes.songs.supabase_service.get_song_by_id", return_value=MOCK_SONG_FROM_DB):
        response = client.get("/song/song-123")
    assert response.status_code == 200
    assert response.json()["id"] == "song-123"
