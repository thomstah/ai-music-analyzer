import os

os.environ.setdefault("GENIUS_ACCESS_TOKEN", "test-genius-token")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("YOUTUBE_API_KEY", "test-youtube-key")
os.environ.setdefault("NEWSAPI_KEY", "test-newsapi-key")


import pytest


@pytest.fixture(autouse=True)
def _reset_claude_budget():
    """Prevent budget state from one test leaking into another."""
    import services.claude_budget as cb
    cb._state["month"] = ""
    cb._state["spend"] = 0.0
    yield


@pytest.fixture(autouse=True)
def _reset_rate_limit_buckets():
    """The token bucket is process-global; clear it between tests so ordering
    doesn't accidentally exhaust the limit before a test even runs."""
    import services.rate_limit as rl
    rl._buckets.clear()
    yield


@pytest.fixture(autouse=True)
def _stub_lyric_search():
    """The /songs/search route calls search_cached_songs_by_lyric, which hits Supabase.
    Default to an empty list so tests don't need to mock it individually — tests that
    care about lyric-match behavior can override via patch inside the test body."""
    from unittest.mock import patch
    with patch("routes.songs.supabase_service.search_cached_songs_by_lyric", return_value=[]):
        yield


@pytest.fixture(autouse=True)
def _stub_album_extras(request):
    """`/album/{id}` calls `_hydrate_album_extras`, which would otherwise hit Genius
    and colorthief live. Only stub for route tests — other test modules (e.g.
    test_color) legitimately exercise the underlying color service and must NOT
    have its attribute patched globally."""
    if request.node.fspath.basename != "test_routes.py":
        yield
        return

    from unittest.mock import patch, AsyncMock
    import routes.songs as songs_route
    songs_route._album_extras_cache.clear()
    with patch("routes.songs.color_service.extract_dominant_color",
               new_callable=AsyncMock, return_value=None), \
         patch("routes.songs.genius_service.get_album_details",
               new_callable=AsyncMock, return_value={}):
        yield
