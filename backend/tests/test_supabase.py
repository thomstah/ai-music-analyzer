from unittest.mock import MagicMock, patch
from services.supabase import find_song, store_song, store_interpretation, get_song_by_id


def _chain(data: list) -> MagicMock:
    """Return a mock Supabase client whose query chain always ends with data."""
    result = MagicMock()
    result.data = data
    client = MagicMock()
    # find_song chain: .table().select().ilike().ilike().limit().execute()
    client.table.return_value.select.return_value.ilike.return_value.ilike.return_value.limit.return_value.execute.return_value = result
    # store_song / store_interpretation chain: .table().insert().execute()
    client.table.return_value.insert.return_value.execute.return_value = result
    # get_song_by_id chain: .table().select().eq().limit().execute()
    client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = result
    return client


def test_find_song_returns_none_when_not_found():
    with patch("services.supabase.get_client", return_value=_chain([])):
        result = find_song("Unknown", "Nobody")
    assert result is None


def test_find_song_returns_first_match():
    song = {"id": "abc", "title": "Bohemian Rhapsody", "artist": "Queen", "interpretations": []}
    with patch("services.supabase.get_client", return_value=_chain([song])):
        result = find_song("Bohemian Rhapsody", "Queen")
    assert result["id"] == "abc"


def test_store_song_returns_inserted_row():
    inserted = {"id": "new-id", "title": "Song", "artist": "Artist", "lyrics": "words"}
    with patch("services.supabase.get_client", return_value=_chain([inserted])):
        result = store_song("Song", "Artist", "words", genius_id=1)
    assert result["id"] == "new-id"


def test_store_interpretation_returns_inserted_row():
    inserted = {"id": "interp-id", "song_id": "song-id", "content": {}, "model_version": "claude-sonnet-4-6"}
    with patch("services.supabase.get_client", return_value=_chain([inserted])):
        result = store_interpretation("song-id", {}, "claude-sonnet-4-6")
    assert result["id"] == "interp-id"


def test_get_song_by_id_returns_none_when_not_found():
    with patch("services.supabase.get_client", return_value=_chain([])):
        result = get_song_by_id("nonexistent-id")
    assert result is None


def test_get_song_by_id_returns_song_when_found():
    song = {"id": "song-id", "title": "Song", "artist": "Artist", "interpretations": []}
    with patch("services.supabase.get_client", return_value=_chain([song])):
        result = get_song_by_id("song-id")
    assert result["id"] == "song-id"
