from unittest.mock import MagicMock, patch
import pytest
from services.supabase import find_song, store_song, store_interpretation, get_song_by_id, find_discourse, store_discourse, get_trending


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


def test_store_song_raises_on_empty_result():
    with patch("services.supabase.get_client", return_value=_chain([])):
        with pytest.raises(RuntimeError, match="Failed to insert song"):
            store_song("Song", "Artist", "words")


def test_store_interpretation_raises_on_empty_result():
    with patch("services.supabase.get_client", return_value=_chain([])):
        with pytest.raises(RuntimeError, match="Failed to insert interpretation"):
            store_interpretation("song-id", {}, "claude-sonnet-4-6")


def test_find_discourse_returns_none_when_not_found():
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("services.supabase.get_client", return_value=client):
        result = find_discourse("song-id")
    assert result is None


def test_find_discourse_returns_row_when_found():
    row = {"id": "disc-1", "song_id": "song-id", "excerpts": [], "scraped_at": "2026-05-29T00:00:00+00:00"}
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [row]
    with patch("services.supabase.get_client", return_value=client):
        result = find_discourse("song-id")
    assert result["id"] == "disc-1"


def test_store_discourse_returns_inserted_row():
    inserted = {"id": "disc-new", "song_id": "song-id", "excerpts": [], "scraped_at": "2026-05-29T00:00:00+00:00"}
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.return_value.data = [inserted]
    with patch("services.supabase.get_client", return_value=client):
        result = store_discourse("song-id", [])
    assert result["id"] == "disc-new"


def test_store_discourse_deletes_existing_before_insert():
    inserted = {"id": "disc-new", "song_id": "song-id", "excerpts": [], "scraped_at": "2026-05-29T00:00:00+00:00"}
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.return_value.data = [inserted]
    with patch("services.supabase.get_client", return_value=client):
        store_discourse("song-id", [])
    client.table.return_value.delete.return_value.eq.assert_called_once_with("song_id", "song-id")
    client.table.return_value.delete.return_value.eq.return_value.execute.assert_called_once()


def test_store_discourse_raises_on_empty_result():
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.return_value.data = []
    with patch("services.supabase.get_client", return_value=client):
        with pytest.raises(RuntimeError, match="Failed to insert discourse"):
            store_discourse("song-id", [])


def test_find_song_increments_request_count_on_cache_hit():
    song = {"id": "abc", "title": "Bohemian Rhapsody", "artist": "Queen", "request_count": 5, "interpretations": []}
    client = MagicMock()
    client.table.return_value.select.return_value.ilike.return_value.ilike.return_value.limit.return_value.execute.return_value.data = [song]
    with patch("services.supabase.get_client", return_value=client):
        result = find_song("Bohemian Rhapsody", "Queen")
    client.table.return_value.update.assert_called_once_with({"request_count": 6})
    client.table.return_value.update.return_value.eq.assert_called_once_with("id", "abc")
    assert result["id"] == "abc"


def test_get_trending_returns_songs_ordered_by_count():
    songs = [
        {"id": "a", "title": "Hit Song", "artist": "Artist A", "request_count": 100},
        {"id": "b", "title": "Another Hit", "artist": "Artist B", "request_count": 50},
    ]
    client = MagicMock()
    client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = songs
    with patch("services.supabase.get_client", return_value=client):
        result = get_trending(10)
    assert result[0]["request_count"] == 100
    assert result[1]["request_count"] == 50


def test_get_trending_returns_empty_list_when_no_songs():
    client = MagicMock()
    client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    with patch("services.supabase.get_client", return_value=client):
        result = get_trending(10)
    assert result == []


def test_search_cached_albums_strips_special_chars_from_query():
    client = MagicMock()
    # Both query chains return empty
    client.table.return_value.select.return_value.or_.return_value.not_.is_.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    client.table.return_value.select.return_value.ilike.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    with patch("services.supabase.get_client", return_value=client):
        from services.supabase import search_cached_albums
        result = search_cached_albums('foo,bar"baz')
    # Verify the or_ call received a sanitized pattern (no commas, no quotes)
    or_call_args = client.table.return_value.select.return_value.or_.call_args
    filter_str = or_call_args[0][0]
    assert 'foobarbaz' in filter_str
    assert '"' in filter_str  # the pattern wrapping quotes
    assert result == []


def test_search_cached_albums_also_queries_by_album_name():
    # The album-name JSONB query must be fired alongside the title/artist search
    client = MagicMock()
    client.table.return_value.select.return_value.or_.return_value.not_.is_.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    client.table.return_value.select.return_value.ilike.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    with patch("services.supabase.get_client", return_value=client):
        from services.supabase import search_cached_albums
        search_cached_albums("ctrl")
    ilike_call = client.table.return_value.select.return_value.ilike.call_args
    assert ilike_call[0][0] == "metadata->>album_name"
    assert "ctrl" in ilike_call[0][1]


def test_search_cached_albums_returns_empty_for_empty_query_after_sanitization():
    with patch("services.supabase.get_client") as mock_client:
        from services.supabase import search_cached_albums
        result = search_cached_albums(',,,"""')
    assert result == []
    mock_client.assert_not_called()


def _sim_row(song_id, title, artist, themes, tone, tldr=None, art=None):
    return {
        "content": {"themes": themes, "emotional_tone": tone, "tldr": tldr},
        "songs": {
            "id": song_id,
            "title": title,
            "artist": artist,
            "metadata": {"album_art_url": art},
        },
    }


def test_find_similar_songs_scores_shared_themes_first():
    from services.supabase import find_similar_songs

    reference = _sim_row("s1", "A", "Artist X", ["grief", "memory"], "melancholy")
    other_high = _sim_row("s2", "B", "Artist X", ["grief", "memory"], "melancholy")  # 3+3+1+2=9
    other_mid = _sim_row("s3", "C", "Artist Y", ["grief"], "hopeful")               # 3
    other_low = _sim_row("s4", "D", "Artist Z", ["joy"], "hopeful")                 # 0 (dropped)

    ref_result = MagicMock(); ref_result.data = [reference]
    cand_result = MagicMock(); cand_result.data = [other_high, other_mid, other_low]

    ref_chain = MagicMock()
    ref_chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = ref_result
    cand_chain = MagicMock()
    cand_chain.select.return_value.neq.return_value.limit.return_value.execute.return_value = cand_result

    client = MagicMock()
    client.table.side_effect = [ref_chain, cand_chain]

    with patch("services.supabase.get_client", return_value=client):
        results = find_similar_songs("s1", limit=3)

    assert [r["id"] for r in results] == ["s2", "s3"]
    assert results[0]["shared_themes"] == ["grief", "memory"]
    assert results[1]["shared_themes"] == ["grief"]
    assert results[0]["score"] > results[1]["score"]


def test_find_similar_songs_returns_empty_when_reference_missing():
    from services.supabase import find_similar_songs

    ref_result = MagicMock(); ref_result.data = []
    ref_chain = MagicMock()
    ref_chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = ref_result

    client = MagicMock()
    client.table.return_value = ref_chain

    with patch("services.supabase.get_client", return_value=client):
        assert find_similar_songs("does-not-exist") == []
