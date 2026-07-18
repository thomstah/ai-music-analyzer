# Artist Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Genius-style artist page with a banner (header background + circular profile photo), short bio, popular songs (clickable to analyze), and popular albums. Artist names across the app become clickable to navigate to the artist page.

**Architecture:**
- **Genius** is the primary source for artist metadata (bio, alternate names, header image, ID linkage with songs/albums we already store)
- **Deezer** (no-auth public API) is the source for popular albums and the high-res circular profile picture — Genius's `/artists/{id}/albums` is forbidden on our access tier
- **Bridging:** when first resolving an artist, look up the Deezer ID by name. Store both `genius_id` and `deezer_id` on the cached artist row
- **Caching:** new `artists` table in Supabase. First visit fetches + stores; subsequent visits read from DB

**Tech Stack:** FastAPI, Python, Next.js 14 App Router, TypeScript, Tailwind CSS, Supabase, Genius API (existing), Deezer API (new, no auth).

---

## File Map

### Backend

| File | Change |
|---|---|
| `backend/migrations/009_artists.sql` | Create — `artists` table |
| `backend/services/genius.py` | Add `get_artist_details(artist_id)`, `search_artist_by_name(name)`; update `get_song_details` to include `artist_id`; update `get_album_details` to include `artist_id` |
| `backend/services/deezer.py` | Create — Deezer client with `search_artist_by_name`, `get_artist_albums`, `get_artist_picture` |
| `backend/services/supabase.py` | Add `find_artist_by_genius_id`, `store_artist`, `get_artist_by_id` |
| `backend/routes/songs.py` | Add `GET /artist/{id}` and `GET /artist/by-name` routes |
| `backend/models/schemas.py` | Add `ArtistTopSong`, `ArtistTopAlbum`, `ArtistResponse`; add `artist_id` to `SongMetadata` and `AlbumResponse` |
| `backend/tests/test_genius.py`, `test_deezer.py`, `test_routes.py` | Tests |

### Frontend

| File | Change |
|---|---|
| `frontend/types/song.ts` | Add `Artist`, `ArtistTopSong`, `ArtistTopAlbum`; add `artist_id` to `SongMetadata` and `Album` |
| `frontend/lib/api.ts` | Add `getArtistById(id)`, `lookupArtistByName(name)` |
| `frontend/components/ArtistBanner.tsx` | Create — header bg + circular photo + name + AKAs + bio |
| `frontend/components/ArtistTopSongs.tsx` | Create — clickable song cards that trigger analyze |
| `frontend/components/ArtistTopAlbums.tsx` | Create — clickable album cards linking to search |
| `frontend/app/artist/[id]/page.tsx` | Create — artist page |
| `frontend/components/SongBanner.tsx` | Artist text becomes a `<Link>` when `artist_id` present |
| `frontend/components/AlbumBanner.tsx` | Artist text becomes a `<Link>` when `artist_id` present |
| `frontend/components/SearchResultsList.tsx` | `ArtistRow` `<button>` → `<Link href={/artist/${artist_id}}>` |
| `frontend/components/BillboardChart.tsx` | Artist name becomes a separate clickable element that does a name lookup and navigates |

---

## Task 1: Backend — schemas, services, route, migration

### 1A — Migration

- [ ] **Step 1: Create `backend/migrations/009_artists.sql`**

```sql
create table if not exists artists (
  id uuid primary key default gen_random_uuid(),
  genius_id integer unique,
  deezer_id integer,
  name text not null,
  alternate_names jsonb default '[]'::jsonb,
  image_url text,
  header_image_url text,
  description_preview text,
  top_songs jsonb default '[]'::jsonb,
  top_albums jsonb default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists artists_genius_id_idx on artists(genius_id);
```

User runs this in Supabase SQL Editor before testing. Unit tests use mocks.

### 1B — Deezer service (new)

- [ ] **Step 2: Write failing test in `backend/tests/test_deezer.py`**

Create the file:
```python
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import services.deezer as deezer


@pytest.mark.asyncio
async def test_search_artist_by_name_returns_first_match():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"id": 246791, "name": "Drake", "picture_xl": "https://img/x.jpg"}
        ]
    }
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await deezer.search_artist_by_name("Drake")
    assert result == {"id": 246791, "name": "Drake", "picture_xl": "https://img/x.jpg"}


@pytest.mark.asyncio
async def test_search_artist_by_name_returns_none_when_empty():
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": []}
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await deezer.search_artist_by_name("xyz nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_get_artist_albums_filters_to_full_albums_and_dedupes():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"id": 1, "title": "Album One", "cover_xl": "u1", "release_date": "2024-01-15", "record_type": "album", "fans": 100},
            {"id": 2, "title": "Album One (Deluxe)", "cover_xl": "u2", "release_date": "2024-02-15", "record_type": "album", "fans": 50},
            {"id": 3, "title": "Single Track", "cover_xl": "u3", "release_date": "2023-11-15", "record_type": "single", "fans": 200},
        ]
    }
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        albums = await deezer.get_artist_albums(246791, limit=10)
    # Singles excluded; both Album One variants kept (different IDs, full albums)
    assert len(albums) == 2
    assert albums[0]["title"] == "Album One"
    assert albums[0]["cover_url"] == "u1"
    assert albums[0]["release_year"] == "2024"


@pytest.mark.asyncio
async def test_get_artist_albums_returns_empty_on_error():
    import httpx as _httpx
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=_httpx.RequestError("network", request=MagicMock())
        )
        result = await deezer.get_artist_albums(123)
    assert result == []
```

Run: `cd backend && pytest tests/test_deezer.py -v` — expected FAIL (module missing).

- [ ] **Step 3: Create `backend/services/deezer.py`**

```python
import logging
import re
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

DEEZER_API_BASE = "https://api.deezer.com"


async def search_artist_by_name(name: str) -> Optional[dict]:
    """Search Deezer for an artist by name. Returns the first hit or None."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{DEEZER_API_BASE}/search/artist",
                params={"q": name, "limit": 1},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError):
        return None
    hits = data.get("data") or []
    if not hits:
        return None
    return hits[0]


async def get_artist_albums(deezer_artist_id: int, limit: int = 6) -> list[dict]:
    """Fetch the artist's full-album discography from Deezer, excluding singles/EPs.
    Returned shape: [{album_id_deezer, title, cover_url, release_year, fans}]"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{DEEZER_API_BASE}/artist/{deezer_artist_id}/albums",
                params={"limit": 50},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError):
        return []
    raw = data.get("data") or []
    albums = []
    for a in raw:
        if a.get("record_type") != "album":
            continue
        release_date = a.get("release_date", "") or ""
        year_match = re.search(r"^(\d{4})", release_date)
        albums.append({
            "album_id_deezer": a.get("id"),
            "title": a.get("title", ""),
            "cover_url": a.get("cover_xl") or a.get("cover_big"),
            "release_year": year_match.group(1) if year_match else None,
            "fans": a.get("fans", 0),
        })
        if len(albums) >= limit:
            break
    return albums
```

Run tests: `pytest tests/test_deezer.py -v` — expected PASS.

### 1C — Genius service additions

- [ ] **Step 4: Add `get_artist_details` and `search_artist_by_name` to `backend/services/genius.py`**

Append at end of file:
```python
async def get_artist_details(artist_id: int) -> dict:
    """Fetch artist bio, header image, alternate names from Genius."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GENIUS_API_BASE}/artists/{artist_id}",
                params={"text_format": "plain"},
                headers={"Authorization": f"Bearer {settings.genius_access_token}"},
            )
            response.raise_for_status()
            artist = response.json()["response"]["artist"]
    except (httpx.HTTPStatusError, httpx.RequestError, KeyError, ValueError):
        return {}

    description = artist.get("description") or {}
    # Genius description.plain is the long form; description_preview is short
    description_preview = ""
    if isinstance(description, dict):
        # 'plain' field with the full text; truncate ourselves to keep it tight
        full = (description.get("plain") or "").strip()
        if full:
            description_preview = full[:300] + ("…" if len(full) > 300 else "")

    return {
        "genius_id": artist.get("id"),
        "name": artist.get("name", ""),
        "alternate_names": artist.get("alternate_names") or [],
        "image_url": artist.get("image_url"),
        "header_image_url": artist.get("header_image_url"),
        "description_preview": description_preview,
    }


async def get_artist_top_songs(artist_id: int, limit: int = 10) -> list[dict]:
    """Fetch the artist's most popular songs on Genius.
    Returned shape: [{genius_id, title, thumbnail, artist_name}]"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GENIUS_API_BASE}/artists/{artist_id}/songs",
                params={"sort": "popularity", "per_page": limit, "text_format": "plain"},
                headers={"Authorization": f"Bearer {settings.genius_access_token}"},
            )
            response.raise_for_status()
            songs = response.json()["response"].get("songs", [])
    except (httpx.HTTPStatusError, httpx.RequestError, KeyError, ValueError):
        return []
    return [
        {
            "genius_id": s.get("id"),
            "title": s.get("title", ""),
            "thumbnail": s.get("song_art_image_thumbnail_url"),
            "artist_name": s.get("primary_artist_names") or s.get("artist_names") or "",
        }
        for s in songs
        if s.get("id")
    ]


async def search_artist_id_by_name(name: str) -> Optional[int]:
    """Use Genius's search to find an artist ID by name. Returns the primary_artist.id
    from the first song hit whose primary artist matches."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GENIUS_API_BASE}/search",
                params={"q": name},
                headers={"Authorization": f"Bearer {settings.genius_access_token}"},
            )
            response.raise_for_status()
            hits = response.json()["response"].get("hits", [])
    except (httpx.HTTPStatusError, httpx.RequestError, KeyError, ValueError):
        return None
    name_lower = name.lower()
    for h in hits:
        primary = (h.get("result") or {}).get("primary_artist") or {}
        if primary.get("id") and name_lower in (primary.get("name") or "").lower():
            return primary["id"]
    # Fall back to first hit's primary artist if no name match
    if hits:
        primary = (hits[0].get("result") or {}).get("primary_artist") or {}
        return primary.get("id")
    return None
```

`Optional` is already imported via `from typing import Optional` — verify at top of file.

- [ ] **Step 5: Update `get_song_details` and `get_album_details` to include `artist_id`**

In `get_song_details`, the return dict — add `artist_id` as the first key:
```python
    return {
        "artist_id": (song.get("primary_artist") or {}).get("id"),
        "album_id": album.get("id"),
        "album_art_url": song.get("song_art_image_url"),
        "album_name": album.get("name"),
        "release_year": release_year,
        "producer": producer,
    }
```

Update existing test `test_get_song_details_returns_metadata`. Add `"primary_artist": {"id": 555, "name": "Drake"}` to the mock song dict and assert `result["artist_id"] == 555`.

In `get_album_details`, the return dict — add `artist_id`:
```python
    return {
        "genius_id": album.get("id"),
        "artist_id": (album.get("artist") or {}).get("id"),
        "title": album.get("name", ""),
        "artist": (album.get("artist") or {}).get("name", ""),
        "release_year": release_year,
        "cover_art_url": album.get("cover_art_url"),
        "producers": producers,
        "tracklist": tracklist,
    }
```

Update `test_get_album_details_returns_album_with_tracklist_and_producers`. Add `"id": 130` to the mock `artist` dict and assert `result["artist_id"] == 130`.

- [ ] **Step 6: Add a test for `get_artist_details`** in `backend/tests/test_genius.py`

Add `get_artist_details, get_artist_top_songs` to the import line, then append:
```python
@pytest.mark.asyncio
async def test_get_artist_details_returns_bio_and_image():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": {
            "artist": {
                "id": 130,
                "name": "Drake",
                "alternate_names": ["Aubrey Graham"],
                "image_url": "https://images.genius.com/profile.jpg",
                "header_image_url": "https://images.genius.com/header.jpg",
                "description": {"plain": "Aubrey Drake Graham, born October 24, 1986."},
            }
        }
    }
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await get_artist_details(130)
    assert result["name"] == "Drake"
    assert result["alternate_names"] == ["Aubrey Graham"]
    assert result["image_url"] == "https://images.genius.com/profile.jpg"
    assert result["header_image_url"] == "https://images.genius.com/header.jpg"
    assert "Aubrey Drake Graham" in result["description_preview"]


@pytest.mark.asyncio
async def test_get_artist_top_songs_returns_song_list():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": {
            "songs": [
                {"id": 1, "title": "God's Plan", "song_art_image_thumbnail_url": "u1", "primary_artist_names": "Drake"},
                {"id": 2, "title": "Hotline Bling", "song_art_image_thumbnail_url": "u2", "primary_artist_names": "Drake"},
            ]
        }
    }
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        songs = await get_artist_top_songs(130, limit=10)
    assert len(songs) == 2
    assert songs[0]["title"] == "God's Plan"
    assert songs[0]["genius_id"] == 1


@pytest.mark.asyncio
async def test_get_artist_details_returns_empty_dict_on_error():
    import httpx as _httpx
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=_httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())
        )
        result = await get_artist_details(130)
    assert result == {}
```

Run: `pytest tests/test_genius.py -v` — expected PASS.

### 1D — Supabase service additions

- [ ] **Step 7: Add artist CRUD functions to `backend/services/supabase.py`**

Append:
```python
def find_artist_by_genius_id(genius_artist_id: int) -> Optional[dict]:
    client = get_client()
    result = (
        client.table("artists")
        .select("*")
        .eq("genius_id", genius_artist_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def store_artist(artist_data: dict) -> dict:
    client = get_client()
    result = client.table("artists").upsert(artist_data, on_conflict="genius_id").execute()
    if not result.data:
        raise RuntimeError("Failed to insert artist: no data returned")
    return result.data[0]


def get_artist_by_id(artist_id: str) -> Optional[dict]:
    client = get_client()
    result = (
        client.table("artists")
        .select("*")
        .eq("id", artist_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None
```

### 1E — Schemas

- [ ] **Step 8: Update `backend/models/schemas.py`**

Add `artist_id` to `SongMetadata` as the first field:
```python
class SongMetadata(BaseModel):
    artist_id: Optional[int] = None
    album_id: Optional[int] = None
    album_art_url: Optional[str] = None
    album_name: Optional[str] = None
    release_year: Optional[str] = None
    producer: Optional[str] = None
```

Add `artist_id` to `AlbumResponse`:
```python
class AlbumResponse(BaseModel):
    id: str
    genius_id: Optional[int] = None
    artist_id: Optional[int] = None
    title: str
    artist: str
    release_year: Optional[str] = None
    cover_art_url: Optional[str] = None
    producers: list[str] = []
    tracklist: list[AlbumTrack] = []
```

Add new artist models:
```python
class ArtistTopSong(BaseModel):
    genius_id: int
    title: str
    thumbnail: Optional[str] = None
    artist_name: str = ""


class ArtistTopAlbum(BaseModel):
    album_id_deezer: int
    title: str
    cover_url: Optional[str] = None
    release_year: Optional[str] = None


class ArtistResponse(BaseModel):
    id: str
    genius_id: Optional[int] = None
    deezer_id: Optional[int] = None
    name: str
    alternate_names: list[str] = []
    image_url: Optional[str] = None
    header_image_url: Optional[str] = None
    description_preview: Optional[str] = None
    top_songs: list[ArtistTopSong] = []
    top_albums: list[ArtistTopAlbum] = []
```

### 1F — Routes

- [ ] **Step 9: Add artist routes to `backend/routes/songs.py`**

Add imports at top:
```python
import services.deezer as deezer_service
from models.schemas import AnalyzeRequest, AlbumResponse, ArtistResponse
```

Add helper and routes (after the existing album code):
```python
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


async def _hydrate_artist(genius_artist_id: int) -> Optional[dict]:
    """Fetch artist data from Genius + Deezer and store in our DB. Returns the stored row."""
    genius_data = await genius_service.get_artist_details(genius_artist_id)
    if not genius_data or not genius_data.get("name"):
        return None
    top_songs = await genius_service.get_artist_top_songs(genius_artist_id, limit=10)

    # Bridge to Deezer by name
    deezer_artist = await deezer_service.search_artist_by_name(genius_data["name"])
    deezer_id = (deezer_artist or {}).get("id")
    top_albums = []
    image_url = genius_data.get("image_url")
    if deezer_id:
        top_albums = await deezer_service.get_artist_albums(deezer_id, limit=6)
        # Prefer Deezer's high-res picture
        deezer_picture = (deezer_artist or {}).get("picture_xl") or (deezer_artist or {}).get("picture_big")
        if deezer_picture:
            image_url = deezer_picture

    row = {
        "genius_id": genius_data["genius_id"],
        "deezer_id": deezer_id,
        "name": genius_data["name"],
        "alternate_names": genius_data.get("alternate_names") or [],
        "image_url": image_url,
        "header_image_url": genius_data.get("header_image_url"),
        "description_preview": genius_data.get("description_preview"),
        "top_songs": top_songs,
        "top_albums": top_albums,
    }
    return supabase_service.store_artist(row)


async def _resolve_artist(artist_id: str) -> Optional[dict]:
    # UUID → our DB lookup
    if _UUID_RE.match(artist_id):
        by_uuid = supabase_service.get_artist_by_id(artist_id)
        return by_uuid

    # Otherwise treat as Genius integer ID
    try:
        genius_id_int = int(artist_id)
    except ValueError:
        return None

    cached = supabase_service.find_artist_by_genius_id(genius_id_int)
    if cached:
        return cached

    return await _hydrate_artist(genius_id_int)


@router.get("/artist/{artist_id}", response_model=ArtistResponse)
async def get_artist(artist_id: str):
    artist = await _resolve_artist(artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    return artist


@router.get("/artist/by-name/{name}")
async def lookup_artist_by_name(name: str):
    """Resolve an artist name → Genius artist ID. Used by Billboard rows."""
    genius_id = await genius_service.search_artist_id_by_name(name)
    if not genius_id:
        raise HTTPException(status_code=404, detail="Artist not found")
    return {"genius_id": genius_id}
```

The `_UUID_RE` already exists in this file for albums — if so, reuse it (don't re-declare). If you're scoping it for the album resolver only, hoist it to module level.

- [ ] **Step 10: Add route tests in `backend/tests/test_routes.py`**

Append:
```python
MOCK_ARTIST = {
    "id": "artist-uuid-1",
    "genius_id": 130,
    "deezer_id": 246791,
    "name": "Drake",
    "alternate_names": ["Aubrey Graham"],
    "image_url": "https://img/drake.jpg",
    "header_image_url": "https://img/drake_header.jpg",
    "description_preview": "Canadian rapper.",
    "top_songs": [{"genius_id": 1, "title": "God's Plan", "thumbnail": None, "artist_name": "Drake"}],
    "top_albums": [{"album_id_deezer": 100, "title": "Scorpion", "cover_url": None, "release_year": "2018"}],
}


def test_get_artist_by_genius_id_returns_cached():
    with patch("routes.songs.supabase_service.find_artist_by_genius_id", return_value=MOCK_ARTIST):
        response = client.get("/artist/130")
    assert response.status_code == 200
    assert response.json()["name"] == "Drake"
    assert response.json()["top_songs"][0]["title"] == "God's Plan"


def test_get_artist_hydrates_when_not_cached():
    with patch("routes.songs.supabase_service.find_artist_by_genius_id", return_value=None), \
         patch("routes.songs.genius_service.get_artist_details", new_callable=AsyncMock, return_value={"genius_id": 130, "name": "Drake", "alternate_names": [], "image_url": "u", "header_image_url": "h", "description_preview": "bio"}), \
         patch("routes.songs.genius_service.get_artist_top_songs", new_callable=AsyncMock, return_value=[]), \
         patch("routes.songs.deezer_service.search_artist_by_name", new_callable=AsyncMock, return_value={"id": 246791, "picture_xl": "dx"}), \
         patch("routes.songs.deezer_service.get_artist_albums", new_callable=AsyncMock, return_value=[]), \
         patch("routes.songs.supabase_service.store_artist", return_value=MOCK_ARTIST):
        response = client.get("/artist/130")
    assert response.status_code == 200
    assert response.json()["name"] == "Drake"


def test_get_artist_returns_404_when_not_found():
    with patch("routes.songs.supabase_service.find_artist_by_genius_id", return_value=None), \
         patch("routes.songs.genius_service.get_artist_details", new_callable=AsyncMock, return_value={}):
        response = client.get("/artist/9999999")
    assert response.status_code == 404


def test_artist_by_name_returns_genius_id():
    with patch("routes.songs.genius_service.search_artist_id_by_name", new_callable=AsyncMock, return_value=130):
        response = client.get("/artist/by-name/Drake")
    assert response.status_code == 200
    assert response.json()["genius_id"] == 130


def test_artist_by_name_returns_404_when_no_match():
    with patch("routes.songs.genius_service.search_artist_id_by_name", new_callable=AsyncMock, return_value=None):
        response = client.get("/artist/by-name/zzz")
    assert response.status_code == 404
```

Run all backend tests: `pytest tests/ -q` — expected all PASS.

### 1G — Commit

- [ ] **Step 11: Commit**

```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer
git add backend/migrations/009_artists.sql \
  backend/services/genius.py backend/services/deezer.py backend/services/supabase.py \
  backend/routes/songs.py backend/models/schemas.py \
  backend/tests/test_genius.py backend/tests/test_deezer.py backend/tests/test_routes.py
git commit -m "feat: artist API — Genius bio + Deezer albums + /artist/{id} route"
```

---

## Task 2: Frontend — artist page

### 2A — Types and API client

- [ ] **Step 1: Update `frontend/types/song.ts`**

Add `artist_id` to `SongMetadata`:
```typescript
export interface SongMetadata {
  artist_id: number | null;
  album_id: number | null;
  album_art_url: string | null;
  album_name: string | null;
  release_year: string | null;
  producer: string | null;
}
```

Add `artist_id` to `Album`:
```typescript
export interface Album {
  id: string;
  genius_id: number | null;
  artist_id: number | null;
  title: string;
  artist: string;
  release_year: string | null;
  cover_art_url: string | null;
  producers: string[];
  tracklist: AlbumTrack[];
}
```

Add artist types:
```typescript
export interface ArtistTopSong {
  genius_id: number;
  title: string;
  thumbnail: string | null;
  artist_name: string;
}

export interface ArtistTopAlbum {
  album_id_deezer: number;
  title: string;
  cover_url: string | null;
  release_year: string | null;
}

export interface Artist {
  id: string;
  genius_id: number | null;
  deezer_id: number | null;
  name: string;
  alternate_names: string[];
  image_url: string | null;
  header_image_url: string | null;
  description_preview: string | null;
  top_songs: ArtistTopSong[];
  top_albums: ArtistTopAlbum[];
}
```

- [ ] **Step 2: Add `getArtistById` and `lookupArtistByName` to `frontend/lib/api.ts`**

Update import line:
```typescript
import { Song, SearchResults, BillboardSong, Article, TrendingTheme, Album, Artist } from '@/types/song';
```

Append:
```typescript
export async function getArtistById(artistId: string | number): Promise<Artist | null> {
  const res = await fetch(`${BASE_URL}/artist/${artistId}`, { cache: 'no-store' });
  if (!res.ok) return null;
  return res.json();
}

export async function lookupArtistByName(name: string): Promise<number | null> {
  const res = await fetch(`${BASE_URL}/artist/by-name/${encodeURIComponent(name)}`, { cache: 'no-store' });
  if (!res.ok) return null;
  const data = await res.json() as { genius_id: number };
  return data.genius_id;
}
```

### 2B — ArtistBanner component

- [ ] **Step 3: Create `frontend/components/ArtistBanner.tsx`**

```tsx
'use client';
import { Artist } from '@/types/song';

export default function ArtistBanner({ artist }: { artist: Artist }) {
  const header = artist.header_image_url;
  const photo = artist.image_url;

  return (
    <div className="relative overflow-hidden rounded-xl mb-8 min-h-56">
      {/* Header background */}
      {header && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={header}
          alt=""
          aria-hidden
          className="absolute inset-0 w-full h-full object-cover scale-110 blur-xl opacity-40"
        />
      )}
      <div className="absolute inset-0 bg-gradient-to-b from-black/70 via-black/60 to-neutral-950" />

      <div className="relative z-10 flex flex-col sm:flex-row items-center sm:items-end gap-6 p-6">
        {photo && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={photo}
            alt={`${artist.name} photo`}
            width={140}
            height={140}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
            className="rounded-full shadow-2xl object-cover w-32 h-32 sm:w-36 sm:h-36 shrink-0 ring-2 ring-neutral-700"
          />
        )}
        <div className="min-w-0 text-center sm:text-left">
          <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest mb-1">Artist</p>
          <h1 className="text-4xl font-black text-white leading-tight">{artist.name}</h1>
          {artist.alternate_names.length > 0 && (
            <p className="text-neutral-400 text-sm mt-1">
              <span className="text-neutral-500">AKA</span> {artist.alternate_names.join(', ')}
            </p>
          )}
          {artist.description_preview && (
            <p className="text-neutral-300 text-sm leading-relaxed mt-3 max-w-2xl">
              {artist.description_preview}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
```

### 2C — ArtistTopSongs component

- [ ] **Step 4: Create `frontend/components/ArtistTopSongs.tsx`**

```tsx
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArtistTopSong, Song } from '@/types/song';
import { analyzeSong } from '@/lib/api';
import Spinner from '@/components/Spinner';

export default function ArtistTopSongs({
  songs,
  artistName,
}: {
  songs: ArtistTopSong[];
  artistName: string;
}) {
  const router = useRouter();
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (songs.length === 0) {
    return <p className="text-neutral-500 text-sm">No popular songs found.</p>;
  }

  async function handleSelect(s: ArtistTopSong) {
    if (loadingId !== null) return;
    setLoadingId(s.genius_id);
    setError(null);
    try {
      const song: Song = await analyzeSong(s.title, artistName);
      sessionStorage.setItem(`song-${song.id}`, JSON.stringify(song));
      router.push(`/song/${song.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setLoadingId(null);
    }
  }

  return (
    <div>
      {error && <p className="text-red-400 text-xs mb-3">{error}</p>}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {songs.map(s => (
          <button
            key={s.genius_id}
            onClick={() => handleSelect(s)}
            disabled={loadingId !== null}
            className="flex items-center gap-4 bg-neutral-900 hover:bg-neutral-800 disabled:opacity-60 rounded-lg p-3 transition-colors text-left"
          >
            {s.thumbnail ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={s.thumbnail}
                alt=""
                width={56}
                height={56}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
                className="w-14 h-14 rounded object-cover shrink-0"
              />
            ) : (
              <div className="w-14 h-14 rounded bg-neutral-700 shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-white font-semibold truncate">{s.title}</p>
              <p className="text-neutral-400 text-sm truncate">{s.artist_name}</p>
            </div>
            <div className="w-4 h-4 shrink-0 flex items-center justify-center">
              {loadingId === s.genius_id && <Spinner size="sm" />}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
```

### 2D — ArtistTopAlbums component

- [ ] **Step 5: Create `frontend/components/ArtistTopAlbums.tsx`**

Albums here come from Deezer (`album_id_deezer`). Since our album pages use Genius album IDs, clicking a Deezer album links to a search query so the user can find/analyze related content.

```tsx
import Link from 'next/link';
import { ArtistTopAlbum } from '@/types/song';

export default function ArtistTopAlbums({
  albums,
  artistName,
}: {
  albums: ArtistTopAlbum[];
  artistName: string;
}) {
  if (albums.length === 0) {
    return <p className="text-neutral-500 text-sm">No popular albums found.</p>;
  }
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4">
      {albums.map(a => (
        <Link
          key={a.album_id_deezer}
          href={`/?q=${encodeURIComponent(`${artistName} ${a.title}`)}`}
          className="block group"
        >
          {a.cover_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={a.cover_url}
              alt={a.title}
              width={200}
              height={200}
              onError={(e) => { e.currentTarget.style.display = 'none'; }}
              className="w-full aspect-square rounded-lg object-cover shadow-lg group-hover:opacity-80 transition-opacity"
            />
          ) : (
            <div className="w-full aspect-square rounded-lg bg-neutral-800" />
          )}
          <p className="text-white text-sm font-medium mt-2 truncate group-hover:text-purple-300 transition-colors">
            {a.title}
          </p>
          {a.release_year && (
            <p className="text-neutral-500 text-xs">{a.release_year}</p>
          )}
        </Link>
      ))}
    </div>
  );
}
```

### 2E — Artist page

- [ ] **Step 6: Create `frontend/app/artist/[id]/page.tsx`**

```tsx
import { getArtistById } from '@/lib/api';
import ArtistBanner from '@/components/ArtistBanner';
import ArtistTopSongs from '@/components/ArtistTopSongs';
import ArtistTopAlbums from '@/components/ArtistTopAlbums';

export default async function ArtistPage({ params }: { params: { id: string } }) {
  const artist = await getArtistById(params.id);

  if (!artist) {
    return (
      <main className="max-w-6xl mx-auto px-6 py-8">
        <p className="text-red-400 text-sm">Artist not found.</p>
      </main>
    );
  }

  return (
    <main className="max-w-6xl mx-auto px-6 py-8">
      <ArtistBanner artist={artist} />

      {artist.top_songs.length > 0 && (
        <section className="mb-10">
          <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">
            Popular {artist.name} Songs
          </h2>
          <ArtistTopSongs songs={artist.top_songs} artistName={artist.name} />
        </section>
      )}

      {artist.top_albums.length > 0 && (
        <section>
          <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">
            Popular {artist.name} Albums
          </h2>
          <ArtistTopAlbums albums={artist.top_albums} artistName={artist.name} />
        </section>
      )}
    </main>
  );
}
```

- [ ] **Step 7: TypeScript check**

```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/frontend
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 8: Commit**

```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer
git add frontend/types/song.ts frontend/lib/api.ts \
  frontend/components/ArtistBanner.tsx \
  frontend/components/ArtistTopSongs.tsx frontend/components/ArtistTopAlbums.tsx \
  frontend/app/artist/
git commit -m "feat: artist page with banner, top songs, top albums (Deezer)"
```

---

## Task 3: Wire artist links across the app

### 3A — SongBanner

- [ ] **Step 1: Update `frontend/components/SongBanner.tsx`**

Read the current file. The artist text is currently:
```tsx
<p className="text-neutral-300 text-lg mt-1">{song.artist}</p>
```

Add `Link` import at top:
```tsx
import Link from 'next/link';
```

Replace the artist line with:
```tsx
{song.metadata?.artist_id ? (
  <Link
    href={`/artist/${song.metadata.artist_id}`}
    className="text-neutral-300 text-lg mt-1 inline-block hover:text-purple-300 transition-colors"
  >
    {song.artist}
  </Link>
) : (
  <p className="text-neutral-300 text-lg mt-1">{song.artist}</p>
)}
```

### 3B — AlbumBanner

- [ ] **Step 2: Update `frontend/components/AlbumBanner.tsx`**

Add `Link` import:
```tsx
import Link from 'next/link';
```

Find the artist line:
```tsx
<p className="text-neutral-300 text-lg mt-1">{album.artist}</p>
```

Replace with:
```tsx
{album.artist_id ? (
  <Link
    href={`/artist/${album.artist_id}`}
    className="text-neutral-300 text-lg mt-1 inline-block hover:text-purple-300 transition-colors"
  >
    {album.artist}
  </Link>
) : (
  <p className="text-neutral-300 text-lg mt-1">{album.artist}</p>
)}
```

### 3C — Search Artists sidebar

- [ ] **Step 3: Update `frontend/components/SearchResultsList.tsx`**

Find the `ArtistRow` component. It's currently a `<button>` with `onClick={onClick}` that calls `handleArtistSelect` which navigates to `/?q=...`. Replace the button with a `Link` to `/artist/{artist_id}`.

Current:
```tsx
function ArtistRow({ artist, onClick }: { artist: ArtistResult; onClick: () => void }) {
  return (
    <button onClick={onClick} className="...">
      ...
    </button>
  );
}
```

Change to:
```tsx
function ArtistRow({ artist }: { artist: ArtistResult }) {
  return (
    <Link
      href={`/artist/${artist.artist_id}`}
      className="w-full flex items-center gap-4 bg-neutral-900 hover:bg-neutral-800 rounded-lg px-4 py-3 transition-colors text-left"
    >
      ...
    </Link>
  );
}
```

Update the call site (also in this file) — remove the `onClick={() => handleArtistSelect(a)}` prop and the now-unused `handleArtistSelect` function.

### 3D — Billboard chart artist names

- [ ] **Step 4: Update `frontend/components/BillboardChart.tsx`**

The artist name needs to become a separately-clickable element that does an async name lookup, then navigates. The rest of the row still triggers song analyze.

Add imports:
```tsx
import { lookupArtistByName } from '@/lib/api';
```

Inside the component, add another loading state and a handler:
```tsx
const [artistLookupKey, setArtistLookupKey] = useState<string | null>(null);

async function handleArtistClick(e: React.MouseEvent, song: BillboardSong) {
  e.stopPropagation();
  e.preventDefault();
  if (artistLookupKey) return;
  setArtistLookupKey(song.artist);
  const genius_id = await lookupArtistByName(song.artist);
  setArtistLookupKey(null);
  if (genius_id) {
    router.push(`/artist/${genius_id}`);
  } else {
    setError(`Couldn't find artist "${song.artist}" on Genius`);
  }
}
```

Inside the row's content, change the artist text from:
```tsx
<p className="text-neutral-400 text-sm truncate">{song.artist}</p>
```

To a clickable span that stops propagation:
```tsx
<button
  type="button"
  onClick={(e) => handleArtistClick(e, song)}
  className="text-neutral-400 text-sm truncate hover:text-purple-300 transition-colors text-left inline-flex items-center gap-1"
>
  {song.artist}
  {artistLookupKey === song.artist && <Spinner size="sm" />}
</button>
```

(Nested `<button>` inside a `<button>` is invalid HTML — change the outer `<button>` row to a `<div>` with `onClick`, OR wrap the row in a different element. Cleanest: change the outer row from `<button>` to a `<div role="button" tabIndex={0} onClick={...} onKeyDown={...}>`. Read the current BillboardChart structure carefully and adapt.)

### 3E — Verify and commit

- [ ] **Step 5: TypeScript check**

```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/frontend
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer
git add frontend/components/SongBanner.tsx frontend/components/AlbumBanner.tsx \
  frontend/components/SearchResultsList.tsx frontend/components/BillboardChart.tsx
git commit -m "feat: clickable artist names route to /artist/{id} across the app"
```

---

## Final: push

```bash
git push
```

---

## Notes

- **Migration 009** must be run in Supabase SQL Editor before artist pages work against a real DB.
- **No new env vars.** Deezer's public API has no auth.
- **Existing songs/albums** in the DB lack `artist_id` in their metadata. Re-analyze them (via search) to populate `artist_id` — same backfill pattern as `album_id`. The cached-analyze backfill in `routes/songs.py` already handles this (it fetches full song details when `album_id` is missing; the same call also returns the new `artist_id`).
- **Genius vs Deezer artist photo:** the route prefers Deezer's `picture_xl` (1000×1000, more reliable URLs). If the Deezer search returns no match, we fall back to Genius's `image_url`.
- **Top album click target:** Deezer album IDs don't map to our Genius-based album pages. Clicking an album card navigates to `/?q=<artist> <album>` which surfaces matches via the existing search. Direct Deezer → Genius album linking is a follow-up feature (would need to search Genius by song from the album and resolve the Genius album ID).
- **Billboard artist click adds one round-trip** for the Genius name lookup. With Genius's `/search` taking ~500ms, expect ~0.5–1s spinner before navigation.
