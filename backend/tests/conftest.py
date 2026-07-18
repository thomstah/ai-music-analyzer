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
