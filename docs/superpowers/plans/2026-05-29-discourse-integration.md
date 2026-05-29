# Discourse Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich AI song interpretations with real community commentary from Reddit and Genius annotations, returning both a richer Claude interpretation and raw `community_commentary` excerpts in the API response.

**Architecture:** A new `services/discourse.py` scrapes Reddit (unofficial JSON API) and Genius annotations (referents API). The route handler checks a 7-day Supabase cache before scraping; discourse excerpts are passed to Claude as additional context and returned alongside the interpretation as `community_commentary`.

**Tech Stack:** httpx (already installed), Reddit unofficial JSON API (no key needed), Genius referents API (uses existing token), Supabase `discourse` table, Pydantic v2, FastAPI

---

## File Structure

**Create:**
- `backend/migrations/002_discourse.sql` — SQL for the discourse table
- `backend/services/discourse.py` — Reddit + Genius annotation scraping
- `backend/tests/test_discourse.py` — discourse service unit tests

**Modify:**
- `backend/models/schemas.py` — add `DiscourseExcerpt`, add `community_commentary` to `SongResponse`
- `backend/services/supabase.py` — add `find_discourse`, `store_discourse`
- `backend/services/anthropic.py` — update `generate_interpretation` to accept optional discourse list
- `backend/routes/songs.py` — wire discourse into `/analyze` flow with TTL logic
- `backend/tests/test_supabase.py` — add `find_discourse` and `store_discourse` tests
- `backend/tests/test_anthropic.py` — add discourse-enriched prompt test
- `backend/tests/test_routes.py` — update existing tests with discourse mocks, add commentary tests

---

### Task 1: Supabase discourse table

**Files:**
- Create: `backend/migrations/002_discourse.sql`

No automated tests — this is a database infrastructure step.

- [ ] **Step 1: Save the migration file**

Create `backend/migrations/002_discourse.sql` with this content:

```sql
create table discourse (
  id uuid primary key default gen_random_uuid(),
  song_id uuid not null references songs(id) on delete cascade,
  excerpts jsonb not null,
  scraped_at timestamptz default now()
);
```

- [ ] **Step 2: Run the SQL in Supabase**

Navigate to your Supabase project → SQL Editor, paste the SQL above, and run it.

- [ ] **Step 3: Verify**

In Supabase → Table Editor, confirm `discourse` appears with columns: `id`, `song_id`, `excerpts`, `scraped_at`.

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/002_discourse.sql
git commit -m "chore: add discourse table migration"
```

---

### Task 2: Pydantic schemas

**Files:**
- Modify: `backend/models/schemas.py`
- Modify: `backend/tests/test_routes.py` (add schema smoke tests at top)

- [ ] **Step 1: Write the failing tests**

Add these two tests to the top of `backend/tests/test_routes.py`, before the existing tests:

```python
from models.schemas import DiscourseExcerpt, SongResponse

def test_discourse_excerpt_schema_validates():
    exc = DiscourseExcerpt(
        source="reddit",
        text="This is a great analysis of the song.",
        url="https://reddit.com/r/hiphopheads/comments/abc",
        metadata={"subreddit": "r/hiphopheads"},
    )
    assert exc.source == "reddit"
    assert exc.url == "https://reddit.com/r/hiphopheads/comments/abc"


def test_song_response_accepts_community_commentary():
    exc = DiscourseExcerpt(source="genius", text="annotation", url=None, metadata={"lyric_fragment": "lean"})
    resp = SongResponse(
        id="1", title="Song", artist="Artist", lyrics="words", community_commentary=[exc]
    )
    assert len(resp.community_commentary) == 1
    assert resp.community_commentary[0].source == "genius"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_routes.py::test_discourse_excerpt_schema_validates tests/test_routes.py::test_song_response_accepts_community_commentary -v
```

Expected: FAIL with `ImportError: cannot import name 'DiscourseExcerpt'`

- [ ] **Step 3: Implement the schemas**

Replace the entire contents of `backend/models/schemas.py` with:

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AnalyzeRequest(BaseModel):
    title: str
    artist: str


class LyricBreakdown(BaseModel):
    lyric: str
    breakdown: str


class InterpretationContent(BaseModel):
    overall_meaning: str
    emotional_tone: str
    themes: list[str]
    key_lyric_breakdowns: list[LyricBreakdown]


class DiscourseExcerpt(BaseModel):
    source: str
    text: str
    url: Optional[str] = None
    metadata: dict


class SongResponse(BaseModel):
    id: str
    title: str
    artist: str
    lyrics: str
    genius_id: Optional[int] = None
    created_at: Optional[datetime] = None
    interpretation: Optional[InterpretationContent] = None
    community_commentary: Optional[list[DiscourseExcerpt]] = None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_routes.py::test_discourse_excerpt_schema_validates tests/test_routes.py::test_song_response_accepts_community_commentary -v
```

Expected: PASS

- [ ] **Step 5: Run full suite to check no regressions**

```bash
cd backend && python -m pytest -v
```

Expected: All existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add backend/models/schemas.py backend/tests/test_routes.py
git commit -m "feat: add DiscourseExcerpt schema and community_commentary to SongResponse"
```

---

### Task 3: Supabase discourse functions

**Files:**
- Modify: `backend/services/supabase.py`
- Modify: `backend/tests/test_supabase.py`

- [ ] **Step 1: Write the failing tests**

Add these tests to the bottom of `backend/tests/test_supabase.py`:

```python
from services.supabase import find_discourse, store_discourse


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
    client.table.return_value.delete.return_value.eq.return_value.execute.assert_called_once()


def test_store_discourse_raises_on_empty_result():
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.return_value.data = []
    with patch("services.supabase.get_client", return_value=client):
        with pytest.raises(RuntimeError, match="Failed to insert discourse"):
            store_discourse("song-id", [])
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_supabase.py::test_find_discourse_returns_none_when_not_found -v
```

Expected: FAIL with `ImportError: cannot import name 'find_discourse'`

- [ ] **Step 3: Implement the discourse functions**

Append these two functions to the bottom of `backend/services/supabase.py`:

```python
def find_discourse(song_id: str) -> Optional[dict]:
    client = get_client()
    result = (
        client.table("discourse")
        .select("*")
        .eq("song_id", song_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def store_discourse(song_id: str, excerpts: list[dict]) -> dict:
    client = get_client()
    client.table("discourse").delete().eq("song_id", song_id).execute()
    result = (
        client.table("discourse")
        .insert({"song_id": song_id, "excerpts": excerpts})
        .execute()
    )
    if not result.data:
        raise RuntimeError("Failed to insert discourse: no data returned")
    return result.data[0]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_supabase.py -v
```

Expected: All supabase tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/services/supabase.py backend/tests/test_supabase.py
git commit -m "feat: add find_discourse and store_discourse to supabase service"
```

---

### Task 4: Discourse service

**Files:**
- Create: `backend/services/discourse.py`
- Create: `backend/tests/test_discourse.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_discourse.py` with this content:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_discourse.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'services.discourse'`

- [ ] **Step 3: Implement the discourse service**

Create `backend/services/discourse.py` with this content:

```python
import logging
import httpx
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)

GENIUS_API_BASE = "https://api.genius.com"
REDDIT_HEADERS = {"User-Agent": "ai-music-analyzer/1.0"}
MAX_REDDIT_EXCERPTS = 10
MIN_COMMENT_LENGTH = 50
MAX_THREADS = 5
MAX_COMMENTS_PER_THREAD = 3
MAX_GENIUS_ANNOTATIONS = 5


async def fetch_discourse(genius_id: Optional[int], title: str, artist: str) -> list[dict]:
    excerpts = []
    excerpts.extend(await _fetch_reddit(title, artist))
    if genius_id is not None:
        excerpts.extend(await _fetch_genius_annotations(genius_id))
    return excerpts


async def _fetch_reddit(title: str, artist: str) -> list[dict]:
    excerpts = []
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=REDDIT_HEADERS) as client:
            search_resp = await client.get(
                "https://www.reddit.com/search.json",
                params={"q": f'"{title}" "{artist}"', "sort": "top", "t": "all", "limit": MAX_THREADS, "type": "link"},
            )
            search_resp.raise_for_status()
            threads = search_resp.json()["data"]["children"]

            for thread in threads:
                if len(excerpts) >= MAX_REDDIT_EXCERPTS:
                    break
                td = thread["data"]
                subreddit = td.get("subreddit_name_prefixed", "r/unknown")
                post_id = td.get("id")
                thread_subreddit = td.get("subreddit")
                thread_url = f"https://reddit.com{td.get('permalink', '')}"

                comments_resp = await client.get(
                    f"https://www.reddit.com/r/{thread_subreddit}/comments/{post_id}.json",
                    params={"sort": "top", "limit": MAX_COMMENTS_PER_THREAD + 3},
                )
                comments_resp.raise_for_status()
                comments_data = comments_resp.json()

                if len(comments_data) < 2:
                    continue

                count = 0
                for comment in comments_data[1]["data"]["children"]:
                    if count >= MAX_COMMENTS_PER_THREAD or len(excerpts) >= MAX_REDDIT_EXCERPTS:
                        break
                    body = comment["data"].get("body", "")
                    if len(body) >= MIN_COMMENT_LENGTH and body not in ("[deleted]", "[removed]"):
                        excerpts.append({
                            "source": "reddit",
                            "text": body,
                            "url": thread_url,
                            "metadata": {"subreddit": subreddit},
                        })
                        count += 1
    except Exception as exc:
        logger.warning("Reddit scraping failed: %s", exc)
    return excerpts


async def _fetch_genius_annotations(genius_id: int) -> list[dict]:
    excerpts = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{GENIUS_API_BASE}/referents",
                params={"song_id": genius_id, "text_format": "plain"},
                headers={"Authorization": f"Bearer {settings.genius_access_token}"},
            )
            resp.raise_for_status()
            referents = resp.json()["response"]["referents"]

            def annotation_length(ref):
                anns = ref.get("annotations", [])
                return len(anns[0].get("body", {}).get("plain", "")) if anns else 0

            for ref in sorted(referents, key=annotation_length, reverse=True)[:MAX_GENIUS_ANNOTATIONS]:
                anns = ref.get("annotations", [])
                if not anns:
                    continue
                text = anns[0].get("body", {}).get("plain", "")
                if text:
                    excerpts.append({
                        "source": "genius",
                        "text": text,
                        "url": None,
                        "metadata": {"lyric_fragment": ref.get("fragment", "")},
                    })
    except Exception as exc:
        logger.warning("Genius annotations fetch failed: %s", exc)
    return excerpts
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_discourse.py -v
```

Expected: All 8 tests pass.

- [ ] **Step 5: Run full suite to check no regressions**

```bash
cd backend && python -m pytest -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/services/discourse.py backend/tests/test_discourse.py
git commit -m "feat: add discourse service with Reddit and Genius annotation scraping"
```

---

### Task 5: Anthropic service — discourse enrichment

**Files:**
- Modify: `backend/services/anthropic.py`
- Modify: `backend/tests/test_anthropic.py`

- [ ] **Step 1: Write the failing test**

Add this test to the bottom of `backend/tests/test_anthropic.py`:

```python
@pytest.mark.asyncio
async def test_generate_interpretation_includes_discourse_in_user_message():
    discourse = [
        {
            "source": "reddit",
            "text": "This track is about Drake processing grief after losing a close friend.",
            "url": "https://reddit.com/r/hiphopheads/comments/xyz",
            "metadata": {"subreddit": "r/hiphopheads"},
        },
        {
            "source": "genius",
            "text": "A reference to the Houston lean culture Drake adopted.",
            "url": None,
            "metadata": {"lyric_fragment": "I sipped lean"},
        },
    ]

    captured = []

    async def capture(**kwargs):
        captured.append(kwargs["messages"][0]["content"])
        return _make_response(json.dumps(VALID_INTERPRETATION))

    with patch("services.anthropic.anthropic.AsyncAnthropic") as mock_cls:
        mock_cls.return_value.messages.create = capture
        await generate_interpretation("Passionfruit", "Drake", "lyrics here", discourse=discourse)

    assert len(captured) == 1
    user_content = captured[0]
    assert "Community Commentary" in user_content
    assert "r/hiphopheads" in user_content
    assert "I sipped lean" in user_content
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_anthropic.py::test_generate_interpretation_includes_discourse_in_user_message -v
```

Expected: FAIL with `TypeError: generate_interpretation() got an unexpected keyword argument 'discourse'`

- [ ] **Step 3: Update the anthropic service**

Replace the entire contents of `backend/services/anthropic.py` with:

```python
import json
import anthropic
from typing import Optional
from fastapi import HTTPException
from config import settings

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2000
REQUIRED_KEYS = {"overall_meaning", "emotional_tone", "themes", "key_lyric_breakdowns"}

SYSTEM_PROMPT = """You are a music critic and literary analyst. Analyze the provided song lyrics and return a JSON object with exactly these fields:
- overall_meaning: 2-3 paragraphs interpreting the song's central message and narrative
- emotional_tone: a brief phrase describing the emotional character (e.g. "melancholic and introspective")
- themes: a list of 3-6 theme strings (e.g. ["loss", "memory", "identity"])
- key_lyric_breakdowns: a list of objects, each with "lyric" (a quoted fragment) and "breakdown" (explanation of its significance)

Return ONLY valid JSON. No markdown fences, no explanation outside the JSON object."""


def _is_valid_interpretation(data: object) -> bool:
    return isinstance(data, dict) and REQUIRED_KEYS.issubset(data.keys())


def _build_user_message(title: str, artist: str, lyrics: str, discourse: Optional[list[dict]]) -> str:
    message = f'Song: "{title}" by {artist}\n\nLyrics:\n{lyrics}'
    if not discourse:
        return message

    lines = []
    for exc in discourse:
        source = exc.get("source", "")
        text = exc.get("text", "")
        metadata = exc.get("metadata", {})
        if source == "reddit":
            subreddit = metadata.get("subreddit", "")
            lines.append(f'[reddit] {subreddit}: "{text}"')
        elif source == "genius":
            fragment = metadata.get("lyric_fragment", "")
            lines.append(f'[genius] "{fragment}" → "{text}"')

    if lines:
        message += "\n\nCommunity Commentary (Reddit threads and Genius annotations — use these to inform your interpretation):\n"
        message += "\n".join(lines)
    return message


async def generate_interpretation(
    title: str,
    artist: str,
    lyrics: str,
    discourse: Optional[list[dict]] = None,
) -> tuple[dict, str]:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    user_message = _build_user_message(title, artist, lyrics, discourse)

    response = await client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_message}],
    )
    raw = response.content[0].text

    try:
        parsed = json.loads(raw)
        if _is_valid_interpretation(parsed):
            return parsed, MODEL
    except json.JSONDecodeError:
        pass

    retry = await client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": raw},
            {"role": "user", "content": "Your response was not valid JSON. Return ONLY the JSON object with no other text."},
        ],
    )
    try:
        parsed = json.loads(retry.content[0].text)
        if _is_valid_interpretation(parsed):
            return parsed, MODEL
    except json.JSONDecodeError:
        pass
    raise HTTPException(status_code=502, detail="AI interpretation service failed to return valid JSON")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_anthropic.py -v
```

Expected: All 5 anthropic tests pass.

- [ ] **Step 5: Run full suite**

```bash
cd backend && python -m pytest -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/services/anthropic.py backend/tests/test_anthropic.py
git commit -m "feat: pass discourse excerpts to Claude as community commentary context"
```

---

### Task 6: Route handler — wire discourse

**Files:**
- Modify: `backend/routes/songs.py`
- Modify: `backend/tests/test_routes.py`

- [ ] **Step 1: Write the failing tests**

Add these tests to the bottom of `backend/tests/test_routes.py`:

```python
from datetime import datetime, timezone, timedelta

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
    assert data["community_commentary"] is not None
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
```

Also update the two existing tests that will now fail because they don't mock `find_discourse` and `discourse_service`. Replace `test_analyze_returns_cached_result_when_song_exists` and `test_analyze_runs_full_flow_when_not_cached` with:

```python
def test_analyze_returns_cached_result_when_song_exists():
    fresh_row = {"id": "disc-1", "song_id": "song-123", "excerpts": [], "scraped_at": _fresh_scraped_at()}
    with patch("routes.songs.supabase_service.find_song", return_value=MOCK_SONG_FROM_DB), \
         patch("routes.songs.supabase_service.find_discourse", return_value=fresh_row):
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_routes.py::test_analyze_returns_community_commentary_on_new_song -v
```

Expected: FAIL with `ImportError` or attribute error since `discourse_service` is not yet imported in routes.

- [ ] **Step 3: Implement the route changes**

Replace the entire contents of `backend/routes/songs.py` with:

```python
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Query
from models.schemas import AnalyzeRequest
import services.supabase as supabase_service
import services.genius as genius_service
import services.anthropic as anthropic_service
import services.discourse as discourse_service

router = APIRouter()

DISCOURSE_TTL_DAYS = 7


def _format_cached(song: dict) -> dict:
    interpretations = song.get("interpretations", [])
    latest = interpretations[0] if interpretations else None
    return {
        "id": song["id"],
        "title": song["title"],
        "artist": song["artist"],
        "lyrics": song["lyrics"],
        "genius_id": song.get("genius_id"),
        "created_at": song.get("created_at"),
        "interpretation": latest.get("content") if latest else None,
    }


def _is_discourse_fresh(row: dict) -> bool:
    scraped_at = datetime.fromisoformat(row["scraped_at"].replace("Z", "+00:00"))
    return datetime.now(timezone.utc) - scraped_at < timedelta(days=DISCOURSE_TTL_DAYS)


@router.get("/songs/search")
async def search_cache(title: str = Query(...), artist: str = Query(...)):
    song = supabase_service.find_song(title, artist)
    if not song:
        return {"found": False, "song": None}
    return {"found": True, "song": _format_cached(song)}


@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    cached = supabase_service.find_song(request.title, request.artist)

    if cached:
        song_id = cached["id"]
        discourse_row = supabase_service.find_discourse(song_id)
        if discourse_row and _is_discourse_fresh(discourse_row):
            excerpts = discourse_row["excerpts"]
        else:
            excerpts = await discourse_service.fetch_discourse(
                cached.get("genius_id"), request.title, request.artist
            )
            supabase_service.store_discourse(song_id, excerpts)
        return {**_format_cached(cached), "community_commentary": excerpts}

    genius_data = await genius_service.search_song(request.title, request.artist)
    lyrics = await genius_service.fetch_lyrics(genius_data["url"])
    excerpts = await discourse_service.fetch_discourse(
        genius_data.get("genius_id"), request.title, request.artist
    )
    interpretation, model_version = await anthropic_service.generate_interpretation(
        request.title, request.artist, lyrics, discourse=excerpts
    )
    song = supabase_service.store_song(
        request.title, request.artist, lyrics, genius_data.get("genius_id")
    )
    supabase_service.store_interpretation(song["id"], interpretation, model_version)
    supabase_service.store_discourse(song["id"], excerpts)

    return {
        "id": song["id"],
        "title": song["title"],
        "artist": song["artist"],
        "lyrics": song["lyrics"],
        "genius_id": song.get("genius_id"),
        "created_at": song.get("created_at"),
        "interpretation": interpretation,
        "community_commentary": excerpts,
    }


@router.get("/song/{song_id}")
async def get_song(song_id: str):
    song = supabase_service.get_song_by_id(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return _format_cached(song)
```

- [ ] **Step 4: Run the new tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_routes.py -v
```

Expected: All route tests pass.

- [ ] **Step 5: Run full suite**

```bash
cd backend && python -m pytest -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/songs.py backend/tests/test_routes.py
git commit -m "feat: wire discourse service into analyze route with 7-day TTL cache"
```
