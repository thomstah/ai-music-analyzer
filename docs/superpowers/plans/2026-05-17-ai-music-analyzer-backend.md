# AI Music Analyzer — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI backend that fetches song lyrics from Genius via scraping, generates structured AI interpretations using Claude, and caches everything in Supabase.

**Architecture:** Service-layer architecture — thin route handlers delegate to `genius.py` (search + scrape), `anthropic.py` (prompt + parse), and `supabase.py` (all DB reads/writes). Cache-first: every request checks Supabase before calling any external API.

**Tech Stack:** FastAPI, Python 3.11, httpx, BeautifulSoup4, anthropic SDK (AsyncAnthropic), supabase-py v2, pydantic-settings, pytest + pytest-asyncio, Railway deployment.

---

## File Map

| File | Responsibility |
|------|----------------|
| `backend/main.py` | FastAPI app init, CORS middleware, router registration, /health |
| `backend/config.py` | pydantic-settings — reads env vars from .env |
| `backend/models/schemas.py` | Pydantic request/response models |
| `backend/routes/songs.py` | Route handlers: POST /analyze, GET /songs/search, GET /song/{id} |
| `backend/services/supabase.py` | All Supabase reads/writes |
| `backend/services/genius.py` | Genius API search + BeautifulSoup lyrics scraping + normalization |
| `backend/services/anthropic.py` | Claude prompt construction, async call, JSON parsing with retry |
| `backend/tests/conftest.py` | Stub env vars so imports work without a real .env |
| `backend/tests/test_supabase.py` | Supabase service unit tests |
| `backend/tests/test_genius.py` | Genius service unit tests |
| `backend/tests/test_anthropic.py` | Anthropic service unit tests |
| `backend/tests/test_routes.py` | Route handler tests (services fully mocked) |
| `backend/requirements.txt` | Python dependencies with pinned versions |
| `backend/.env.example` | Example env vars (no real values) |
| `backend/pytest.ini` | asyncio_mode = auto |
| `backend/railway.toml` | Railway build + deploy config |

---

### Task 1: Project Scaffold

**Files:**
- Create: `backend/` directory tree
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/pytest.ini`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Initialize git and create directory structure**

```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer
git init
mkdir -p backend/routes backend/services backend/models backend/tests
touch backend/routes/__init__.py backend/services/__init__.py backend/models/__init__.py backend/tests/__init__.py
```

Expected: directories created, git repository initialized.

- [ ] **Step 2: Create requirements.txt**

Create `backend/requirements.txt`:
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
httpx==0.27.2
beautifulsoup4==4.12.3
anthropic==0.40.0
supabase==2.9.0
pydantic-settings==2.6.1
python-dotenv==1.0.1

# Testing
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 3: Create .env.example**

Create `backend/.env.example`:
```
GENIUS_ACCESS_TOKEN=your_genius_access_token_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_SERVICE_KEY=your_supabase_service_role_key_here
```

- [ ] **Step 4: Create pytest.ini**

Create `backend/pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 5: Create tests/conftest.py**

Create `backend/tests/conftest.py`:
```python
import os

os.environ.setdefault("GENIUS_ACCESS_TOKEN", "test-genius-token")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
```

- [ ] **Step 6: Install dependencies**

```bash
cd backend
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend project structure"
```

---

### Task 2: Supabase Database Setup

**Files:** None — run SQL in the Supabase dashboard SQL Editor.

- [ ] **Step 1: Create the songs table**

In the Supabase dashboard → SQL Editor, run:

```sql
create table songs (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  artist text not null,
  lyrics text not null,
  genius_id integer,
  created_at timestamptz default now()
);
```

Expected: table created, no errors.

- [ ] **Step 2: Create the interpretations table**

```sql
create table interpretations (
  id uuid primary key default gen_random_uuid(),
  song_id uuid not null references songs(id) on delete cascade,
  content jsonb not null,
  model_version text not null,
  created_at timestamptz default now()
);
```

Expected: table created with foreign key to songs.

- [ ] **Step 3: Add index for cache lookups**

```sql
create index songs_title_artist_idx on songs (lower(title), lower(artist));
```

Expected: index created.

---

### Task 3: Config & Pydantic Schemas

**Files:**
- Create: `backend/config.py`
- Create: `backend/models/schemas.py`

- [ ] **Step 1: Write config.py**

Create `backend/config.py`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    genius_access_token: str
    anthropic_api_key: str
    supabase_url: str
    supabase_service_key: str

    model_config = {"env_file": ".env"}

settings = Settings()
```

- [ ] **Step 2: Write models/schemas.py**

Create `backend/models/schemas.py`:
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

class SongResponse(BaseModel):
    id: str
    title: str
    artist: str
    lyrics: str
    genius_id: Optional[int] = None
    created_at: Optional[datetime] = None
    interpretation: Optional[InterpretationContent] = None
```

- [ ] **Step 3: Verify schemas load without error**

```bash
cd backend
python -c "from models.schemas import AnalyzeRequest, SongResponse; print('OK')"
```

Expected output: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/config.py backend/models/
git commit -m "feat: add config and pydantic schemas"
```

---

### Task 4: Supabase Service

**Files:**
- Create: `backend/tests/test_supabase.py`
- Create: `backend/services/supabase.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_supabase.py`:
```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend
pytest tests/test_supabase.py -v
```

Expected: `ImportError` — `services.supabase` does not exist yet.

- [ ] **Step 3: Write services/supabase.py**

Create `backend/services/supabase.py`:
```python
from supabase import create_client, Client
from config import settings
from typing import Optional


def get_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)


def find_song(title: str, artist: str) -> Optional[dict]:
    client = get_client()
    result = (
        client.table("songs")
        .select("*, interpretations(*)")
        .ilike("title", title)
        .ilike("artist", artist)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def store_song(title: str, artist: str, lyrics: str, genius_id: Optional[int] = None) -> dict:
    client = get_client()
    result = (
        client.table("songs")
        .insert({"title": title, "artist": artist, "lyrics": lyrics, "genius_id": genius_id})
        .execute()
    )
    return result.data[0]


def store_interpretation(song_id: str, content: dict, model_version: str) -> dict:
    client = get_client()
    result = (
        client.table("interpretations")
        .insert({"song_id": song_id, "content": content, "model_version": model_version})
        .execute()
    )
    return result.data[0]


def get_song_by_id(song_id: str) -> Optional[dict]:
    client = get_client()
    result = (
        client.table("songs")
        .select("*, interpretations(*)")
        .eq("id", song_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd backend
pytest tests/test_supabase.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/supabase.py backend/tests/test_supabase.py
git commit -m "feat: add supabase service with find, store, and get operations"
```

---

### Task 5: Genius Service

**Files:**
- Create: `backend/tests/test_genius.py`
- Create: `backend/services/genius.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_genius.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from services.genius import search_song, fetch_lyrics, normalize_lyrics


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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend
pytest tests/test_genius.py -v
```

Expected: `ImportError` — `services.genius` does not exist yet.

- [ ] **Step 3: Write services/genius.py**

Create `backend/services/genius.py`:
```python
import re
import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException
from config import settings

GENIUS_API_BASE = "https://api.genius.com"


async def search_song(title: str, artist: str) -> dict:
    query = f"{title} {artist}"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GENIUS_API_BASE}/search",
            params={"q": query},
            headers={"Authorization": f"Bearer {settings.genius_access_token}"},
        )
        response.raise_for_status()

    hits = response.json()["response"]["hits"]
    if not hits:
        raise HTTPException(status_code=404, detail=f"Song '{title}' by '{artist}' not found on Genius")

    hit = hits[0]["result"]
    return {"url": hit["url"], "genius_id": hit["id"]}


async def fetch_lyrics(url: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url)

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not extract lyrics from Genius")

    soup = BeautifulSoup(response.text, "html.parser")
    containers = soup.find_all("div", attrs={"data-lyrics-container": "true"})

    if not containers:
        raise HTTPException(status_code=502, detail="Could not extract lyrics from Genius")

    parts = []
    for container in containers:
        for br in container.find_all("br"):
            br.replace_with("\n")
        parts.append(container.get_text())

    return normalize_lyrics("\n".join(parts))


def normalize_lyrics(lyrics: str) -> str:
    cleaned = re.sub(r"\[.*?\]", "", lyrics)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd backend
pytest tests/test_genius.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/genius.py backend/tests/test_genius.py
git commit -m "feat: add genius service for lyrics search and scraping"
```

---

### Task 6: Anthropic Service

**Files:**
- Create: `backend/tests/test_anthropic.py`
- Create: `backend/services/anthropic.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_anthropic.py`:
```python
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from services.anthropic import generate_interpretation

VALID_INTERPRETATION = {
    "overall_meaning": "A song about existential dread.",
    "emotional_tone": "melancholic",
    "themes": ["mortality", "identity"],
    "key_lyric_breakdowns": [
        {"lyric": "Is this the real life?", "breakdown": "Questions the nature of reality."}
    ],
}


def _make_response(text: str) -> MagicMock:
    content = MagicMock()
    content.text = text
    response = MagicMock()
    response.content = [content]
    return response


@pytest.mark.asyncio
async def test_generate_interpretation_returns_parsed_json_and_model():
    with patch("services.anthropic.anthropic.AsyncAnthropic") as mock_cls:
        mock_cls.return_value.messages.create = AsyncMock(
            return_value=_make_response(json.dumps(VALID_INTERPRETATION))
        )
        result, model = await generate_interpretation("Bohemian Rhapsody", "Queen", "lyrics here")

    assert result["overall_meaning"] == VALID_INTERPRETATION["overall_meaning"]
    assert result["emotional_tone"] == "melancholic"
    assert "mortality" in result["themes"]
    assert model == "claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_generate_interpretation_retries_on_invalid_json():
    bad = _make_response("this is not json")
    good = _make_response(json.dumps(VALID_INTERPRETATION))

    with patch("services.anthropic.anthropic.AsyncAnthropic") as mock_cls:
        mock_cls.return_value.messages.create = AsyncMock(side_effect=[bad, good])
        result, _ = await generate_interpretation("Song", "Artist", "some lyrics")

    assert result["overall_meaning"] == VALID_INTERPRETATION["overall_meaning"]


@pytest.mark.asyncio
async def test_generate_interpretation_raises_502_after_two_failures():
    bad = _make_response("not json at all")

    with patch("services.anthropic.anthropic.AsyncAnthropic") as mock_cls:
        mock_cls.return_value.messages.create = AsyncMock(return_value=bad)
        with pytest.raises(HTTPException) as exc_info:
            await generate_interpretation("Song", "Artist", "lyrics")

    assert exc_info.value.status_code == 502
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend
pytest tests/test_anthropic.py -v
```

Expected: `ImportError` — `services.anthropic` does not exist yet.

- [ ] **Step 3: Write services/anthropic.py**

Create `backend/services/anthropic.py`:
```python
import json
import anthropic
from fastapi import HTTPException
from config import settings

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a music critic and literary analyst. Analyze the provided song lyrics and return a JSON object with exactly these fields:
- overall_meaning: 2-3 paragraphs interpreting the song's central message and narrative
- emotional_tone: a brief phrase describing the emotional character (e.g. "melancholic and introspective")
- themes: a list of 3-6 theme strings (e.g. ["loss", "memory", "identity"])
- key_lyric_breakdowns: a list of objects, each with "lyric" (a quoted fragment) and "breakdown" (explanation of its significance)

Return ONLY valid JSON. No markdown fences, no explanation outside the JSON object."""


async def generate_interpretation(title: str, artist: str, lyrics: str) -> tuple[dict, str]:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    user_message = f'Song: "{title}" by {artist}\n\nLyrics:\n{lyrics}'

    response = await client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_message}],
    )
    raw = response.content[0].text

    try:
        return json.loads(raw), MODEL
    except json.JSONDecodeError:
        pass

    retry = await client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": raw},
            {"role": "user", "content": "Your response was not valid JSON. Return ONLY the JSON object with no other text."},
        ],
    )
    try:
        return json.loads(retry.content[0].text), MODEL
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI interpretation service failed to return valid JSON")
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd backend
pytest tests/test_anthropic.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/anthropic.py backend/tests/test_anthropic.py
git commit -m "feat: add anthropic service with structured JSON interpretation and retry"
```

---

### Task 7: Route Handlers & App Wiring

**Files:**
- Create: `backend/main.py`
- Create: `backend/routes/songs.py` (replace stub)
- Create: `backend/tests/test_routes.py`

- [ ] **Step 1: Write main.py**

Create `backend/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.songs import router

app = FastAPI(title="AI Music Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Write routes/songs.py stub so tests can import**

Create `backend/routes/songs.py`:
```python
from fastapi import APIRouter

router = APIRouter()
```

- [ ] **Step 3: Write failing tests**

Create `backend/tests/test_routes.py`:
```python
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
```

- [ ] **Step 4: Run tests to confirm most fail**

```bash
cd backend
pytest tests/test_routes.py -v
```

Expected: `test_health_returns_ok` passes, route tests fail because routes are not implemented.

- [ ] **Step 5: Implement routes/songs.py**

Replace `backend/routes/songs.py` with:
```python
from fastapi import APIRouter, HTTPException, Query
from models.schemas import AnalyzeRequest
import services.supabase as supabase_service
import services.genius as genius_service
import services.anthropic as anthropic_service

router = APIRouter()


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
        "interpretation": latest["content"] if latest else None,
    }


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
        return _format_cached(cached)

    genius_data = await genius_service.search_song(request.title, request.artist)
    lyrics = await genius_service.fetch_lyrics(genius_data["url"])
    interpretation, model_version = await anthropic_service.generate_interpretation(
        request.title, request.artist, lyrics
    )

    song = supabase_service.store_song(
        request.title, request.artist, lyrics, genius_data.get("genius_id")
    )
    supabase_service.store_interpretation(song["id"], interpretation, model_version)

    return {**song, "interpretation": interpretation}


@router.get("/song/{song_id}")
async def get_song(song_id: str):
    song = supabase_service.get_song_by_id(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return _format_cached(song)
```

- [ ] **Step 6: Run all tests**

```bash
cd backend
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/routes/songs.py backend/tests/test_routes.py backend/main.py
git commit -m "feat: add route handlers and wire up FastAPI app"
```

---

### Task 8: Railway Deployment Config

**Files:**
- Create: `backend/railway.toml`

- [ ] **Step 1: Write railway.toml**

Create `backend/railway.toml`:
```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

- [ ] **Step 2: Verify app starts locally**

```bash
cd backend
cp .env.example .env
# Edit .env and fill in real values, then:
uvicorn main:app --reload
```

Expected: server starts on http://127.0.0.1:8000. `GET /health` returns `{"status": "ok"}`.

- [ ] **Step 3: Run a real end-to-end request against the local server**

```bash
curl -s -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"title": "Bohemian Rhapsody", "artist": "Queen"}' | python3 -m json.tool
```

Expected: JSON response with `id`, `title`, `artist`, `lyrics`, and `interpretation` (with `overall_meaning`, `emotional_tone`, `themes`, `key_lyric_breakdowns`).

- [ ] **Step 4: Commit**

```bash
git add backend/railway.toml
git commit -m "feat: add Railway deployment config"
```

---

## Out of Scope (Not in This Plan)

- Frontend (Next.js)
- Reddit/discourse aggregation (Phase 8)
- pgvector / semantic search embeddings (Phase 8)
- Authentication on the API
- Async job queue for AI calls
- ON CONFLICT handling for concurrent duplicate inserts (acceptable for MVP given cache-first check)
