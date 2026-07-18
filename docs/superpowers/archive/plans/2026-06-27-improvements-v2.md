# Improvements V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Six improvements — pre-warm Billboard cache, music news panel, trending themes, featured artist banner, search redesign with Albums category, and album pages with expandable About.

**Architecture:** Tasks 1–4 build out the home page. Task 5 redesigns search and adds Albums (derived from cached songs in our DB). Task 6 is the largest — album pages with new DB table. Each task commits independently.

**Tech Stack:** FastAPI, Python, Next.js 14 App Router, TypeScript, Tailwind CSS, Supabase, NewsAPI (new free-tier dep).

---

## File Map

### Task 1: Pre-warm Billboard cache

| File | Change |
|---|---|
| `backend/main.py` | Add lifespan handler that fetches Billboard at startup |

### Task 2: NewsAPI music feed

| File | Change |
|---|---|
| `backend/config.py` | Add `newsapi_key` setting |
| `.env` | Add `NEWSAPI_KEY=...` (user-provided) |
| `backend/services/news.py` | Create — NewsAPI fetcher with 1h cache |
| `backend/routes/songs.py` | Add `GET /news` route |
| `backend/models/schemas.py` | Add `Article` model |
| `backend/tests/test_news.py` | Create |
| `backend/tests/test_routes.py` | Add news route test |
| `frontend/types/song.ts` | Add `Article` interface |
| `frontend/lib/api.ts` | Add `getMusicNews()` |
| `frontend/components/NewsPanel.tsx` | Create |
| `frontend/app/page.tsx` | Two-column layout on desktop (Billboard + News) |

### Task 3: Trending themes section

| File | Change |
|---|---|
| `backend/services/supabase.py` | Add `get_trending_themes(limit)` SQL aggregation |
| `backend/routes/songs.py` | Add `GET /trending/themes` |
| `backend/models/schemas.py` | Add `TrendingTheme` |
| `backend/tests/test_routes.py` | Add trending themes test |
| `frontend/types/song.ts` | Add `TrendingTheme` |
| `frontend/lib/api.ts` | Add `getTrendingThemes()` |
| `frontend/components/TrendingThemes.tsx` | Create |
| `frontend/app/page.tsx` | Mount TrendingThemes in right column |

### Task 4: Featured artist banner

| File | Change |
|---|---|
| `frontend/components/FeaturedArtistBanner.tsx` | Create — uses Billboard #1 |
| `frontend/app/page.tsx` | Mount FeaturedArtistBanner above the 2-col layout |

### Task 5: Search redesign with Albums category

| File | Change |
|---|---|
| `backend/services/supabase.py` | Add `search_cached_albums(query)` returning grouped album rows |
| `backend/services/genius.py` | Update `search_songs` to call albums lookup |
| `backend/routes/songs.py` | Update `/songs/search` to include albums in response |
| `backend/models/schemas.py` | Add `AlbumSearchResult` |
| `backend/tests/` | Add albums-in-search tests |
| `frontend/types/song.ts` | Add `AlbumSearchResult`; add `albums` to `SearchResults` |
| `frontend/components/SearchResultsList.tsx` | Restructure layout + Albums section + AlbumCard |

### Task 6: Album page

| File | Change |
|---|---|
| `backend/migrations/007_albums.sql` | Create — `albums` table |
| `backend/services/genius.py` | Add `get_album_details(album_id)` returning basic info + producers list; update `get_song_details` to include `album_id` |
| `backend/services/supabase.py` | Add `find_album`, `store_album`, `get_album_by_id` |
| `backend/routes/songs.py` | Add `GET /album/{album_id}` route |
| `backend/models/schemas.py` | Add `AlbumTrack`, `AlbumResponse`; add `album_id` to `SongMetadata` |
| `backend/tests/test_genius.py` | Add `get_album_details` tests |
| `backend/tests/test_routes.py` | Add `/album/{id}` route tests |
| `frontend/types/song.ts` | Add `Album`, `AlbumTrack`; add `album_id` to `SongMetadata` |
| `frontend/lib/api.ts` | Add `getAlbumById()` |
| `frontend/app/album/[id]/page.tsx` | Create — basic info + tracklist, no About |
| `frontend/components/AlbumBanner.tsx` | Create — shows artist, year, producers |
| `frontend/components/Tracklist.tsx` | Create |
| `frontend/components/SongBanner.tsx` | Make "Album" label clickable when `album_id` exists |

---

## Task 1: Pre-warm Billboard cache at startup

**Goal:** First load of the home page after a backend restart should not pay the 3–5s billboard scrape cost.

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Convert `main.py` to use FastAPI lifespan**

Replace the entire file:
```python
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.songs import router
import services.billboard as billboard_service

logger = logging.getLogger(__name__)


async def _warm_billboard_cache():
    """Pre-warm the Billboard Hot 100 cache so the first home-page load is fast."""
    try:
        await asyncio.to_thread(billboard_service.get_hot_100, 10)
        logger.info("Billboard cache pre-warmed")
    except Exception as exc:
        logger.warning("Failed to pre-warm Billboard cache: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run on startup, don't block boot
    asyncio.create_task(_warm_billboard_cache())
    yield


app = FastAPI(title="AI Music Analyzer", lifespan=lifespan)

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

- [ ] **Step 2: Verify tests still pass**

```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/backend
pytest tests/ -q
```
Expected: all PASS (no test changes needed; existing tests use `TestClient` which triggers lifespan).

- [ ] **Step 3: Commit**

```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer
git add backend/main.py
git commit -m "perf: pre-warm Billboard cache at startup to eliminate cold first load"
```

---

## Task 2: NewsAPI music feed on home page (desktop)

**Prerequisite:** User must create a free NewsAPI account at https://newsapi.org/register and add `NEWSAPI_KEY=<key>` to `backend/.env`. Free tier: 100 requests/day, sufficient for an MVP with 1h cache.

**Files:**
- Create: `backend/services/news.py`
- Modify: `backend/config.py`, `backend/routes/songs.py`, `backend/models/schemas.py`
- Create: `backend/tests/test_news.py`
- Modify: `backend/tests/test_routes.py`
- Modify: `frontend/types/song.ts`, `frontend/lib/api.ts`, `frontend/app/page.tsx`
- Create: `frontend/components/NewsPanel.tsx`

### 2A — Backend

- [ ] **Step 1: Add `newsapi_key` to `backend/config.py`**

```python
class Settings(BaseSettings):
    genius_access_token: str
    anthropic_api_key: str
    supabase_url: str
    supabase_service_key: str
    youtube_api_key: str
    newsapi_key: str = ""  # optional — empty disables the news feature

    model_config = ConfigDict(env_file=".env", extra="ignore")
```

Also update `backend/tests/conftest.py` to set a test value:
```python
os.environ.setdefault("NEWSAPI_KEY", "test-newsapi-key")
```

- [ ] **Step 2: Write failing test for `backend/services/news.py`**

Create `backend/tests/test_news.py`:
```python
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
import services.news as news_module


def _reset_cache():
    news_module._cache["data"] = None
    news_module._cache["fetched_at"] = None


@pytest.mark.asyncio
async def test_get_music_news_returns_articles():
    _reset_cache()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "ok",
        "articles": [
            {
                "title": "New album drops",
                "description": "It's good",
                "url": "https://pitchfork.com/x",
                "urlToImage": "https://img/x.jpg",
                "source": {"name": "Pitchfork"},
                "publishedAt": "2026-06-25T10:00:00Z",
            }
        ],
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await news_module.get_music_news()

    assert len(result) == 1
    assert result[0]["title"] == "New album drops"
    assert result[0]["source"] == "Pitchfork"


@pytest.mark.asyncio
async def test_get_music_news_returns_cached_on_subsequent_call():
    _reset_cache()
    news_module._cache["data"] = [{"title": "Cached"}]
    news_module._cache["fetched_at"] = datetime.now(timezone.utc)

    with patch("httpx.AsyncClient") as mock_cls:
        result = await news_module.get_music_news()
    mock_cls.assert_not_called()
    assert result[0]["title"] == "Cached"


@pytest.mark.asyncio
async def test_get_music_news_returns_empty_on_error():
    _reset_cache()
    import httpx as _httpx
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=_httpx.RequestError("network down", request=MagicMock())
        )
        result = await news_module.get_music_news()
    assert result == []


@pytest.mark.asyncio
async def test_get_music_news_does_not_cache_empty():
    _reset_cache()
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ok", "articles": []}
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await news_module.get_music_news()
    assert result == []
    assert news_module._cache["data"] is None
```

Run: `pytest tests/test_news.py -v` — expected FAIL (module missing).

- [ ] **Step 3: Create `backend/services/news.py`**

```python
import logging
import httpx
from datetime import datetime, timezone, timedelta
from config import settings

logger = logging.getLogger(__name__)

NEWS_API_BASE = "https://newsapi.org/v2"
MUSIC_SOURCES = "pitchfork.com,rollingstone.com,nme.com,billboard.com,stereogum.com"

_cache: dict = {"data": None, "fetched_at": None}
_CACHE_TTL = timedelta(hours=1)


async def get_music_news(limit: int = 8) -> list[dict]:
    now = datetime.now(timezone.utc)
    if (
        _cache["data"] is not None
        and _cache["fetched_at"] is not None
        and now - _cache["fetched_at"] < _CACHE_TTL
    ):
        return _cache["data"][:limit]

    if not settings.newsapi_key:
        return []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{NEWS_API_BASE}/everything",
                params={
                    "q": "music",
                    "domains": MUSIC_SOURCES,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": 20,
                    "apiKey": settings.newsapi_key,
                },
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.warning("NewsAPI fetch failed: %s", exc)
        return _cache["data"][:limit] if _cache["data"] else []

    if data.get("status") != "ok":
        return _cache["data"][:limit] if _cache["data"] else []

    articles = [
        {
            "title": a.get("title", ""),
            "description": a.get("description", ""),
            "url": a.get("url", ""),
            "image_url": a.get("urlToImage"),
            "source": (a.get("source") or {}).get("name", ""),
            "published_at": a.get("publishedAt", ""),
        }
        for a in data.get("articles", [])
        if a.get("title") and a.get("url")
    ]

    if articles:
        _cache["data"] = articles
        _cache["fetched_at"] = now

    return articles[:limit]
```

Run tests: `pytest tests/test_news.py -v` — expected PASS.

- [ ] **Step 4: Add `Article` model to `backend/models/schemas.py`**

```python
class Article(BaseModel):
    title: str
    description: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    source: str
    published_at: str
```

- [ ] **Step 5: Add `GET /news` route to `backend/routes/songs.py`**

Add import at top:
```python
import services.news as news_service
```

Append route:
```python
@router.get("/news")
async def news(limit: int = Query(default=8, ge=1, le=20)):
    return await news_service.get_music_news(limit)
```

- [ ] **Step 6: Add route test in `backend/tests/test_routes.py`**

```python
def test_news_returns_articles():
    articles = [{"title": "Test", "description": "x", "url": "u", "image_url": None, "source": "S", "published_at": "2026-01-01"}]
    with patch("routes.songs.news_service.get_music_news", new_callable=AsyncMock, return_value=articles):
        response = client.get("/news")
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Test"
```

Run all backend tests: `pytest tests/ -q` — expected all PASS.

### 2B — Frontend

- [ ] **Step 7: Add `Article` type to `frontend/types/song.ts`**

```typescript
export interface Article {
  title: string;
  description: string | null;
  url: string;
  image_url: string | null;
  source: string;
  published_at: string;
}
```

- [ ] **Step 8: Add `getMusicNews()` to `frontend/lib/api.ts`**

Update the import line:
```typescript
import { Song, SearchResults, BillboardSong, Article } from '@/types/song';
```

Append:
```typescript
export async function getMusicNews(limit = 8): Promise<Article[]> {
  const res = await fetch(`${BASE_URL}/news?limit=${limit}`, { cache: 'no-store' });
  if (!res.ok) return [];
  return res.json();
}
```

- [ ] **Step 9: Create `frontend/components/NewsPanel.tsx`**

```tsx
import { Article } from '@/types/song';

function formatTimeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const minutes = Math.floor((now - then) / 60000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function NewsPanel({ articles }: { articles: Article[] }) {
  if (articles.length === 0) {
    return (
      <p className="text-neutral-500 text-sm">
        News feed unavailable.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {articles.map(a => (
        <a
          key={a.url}
          href={a.url}
          target="_blank"
          rel="noopener noreferrer"
          className="block bg-neutral-900 hover:bg-neutral-800 rounded-lg overflow-hidden transition-colors"
        >
          <div className="flex gap-3 p-3">
            {a.image_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={a.image_url}
                alt=""
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
                className="w-20 h-20 rounded object-cover shrink-0"
              />
            )}
            <div className="min-w-0 flex-1">
              <p className="text-white font-semibold text-sm leading-snug line-clamp-2">
                {a.title}
              </p>
              <p className="text-neutral-500 text-xs mt-1">
                {a.source} · {formatTimeAgo(a.published_at)}
              </p>
            </div>
          </div>
        </a>
      ))}
    </div>
  );
}
```

(Server component — no `'use client'` needed since `onError` is a DOM attribute that works in client-rendered HTML too; if there are issues, add `'use client'`.)

- [ ] **Step 10: Update `frontend/app/page.tsx` to two-column on desktop, stacked on mobile**

Replace the default (no query) branch only. News must stack below Billboard on mobile (no `hidden lg:block`):

```tsx
const [billboard, articles] = await Promise.all([
  getBillboard(10),
  getMusicNews(8),
]);
return (
  <main className="max-w-6xl mx-auto px-6 py-12">
    <h1 className="text-3xl font-black text-white mb-2">What does it mean?</h1>
    <p className="text-neutral-400 mb-10">
      Search a song to get Lyriq&apos;s interpretation of the lyrics.
    </p>
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
      <section className="lg:col-span-2">
        <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">
          Billboard Hot 100
        </h2>
        <BillboardChart songs={billboard} />
      </section>
      <aside>
        <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">
          Music News
        </h2>
        <NewsPanel articles={articles} />
      </aside>
    </div>
  </main>
);
```

The grid is mobile-first: `grid-cols-1` stacks on mobile, `lg:grid-cols-3` activates the 2/1 split on desktop. News will appear below Billboard on mobile, which matches your preference.

Update imports:
```tsx
import { getBillboard, searchSongs, getMusicNews } from '@/lib/api';
import BillboardChart from '@/components/BillboardChart';
import NewsPanel from '@/components/NewsPanel';
import SearchResultsList from '@/components/SearchResultsList';
```

The search-results branch stays unchanged here (it gets redesigned in Task 5).

- [ ] **Step 11: TypeScript check**

```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/frontend
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 12: Commit**

```bash
git add backend/config.py backend/services/news.py backend/models/schemas.py \
  backend/routes/songs.py backend/tests/test_news.py backend/tests/test_routes.py \
  backend/tests/conftest.py \
  frontend/types/song.ts frontend/lib/api.ts frontend/components/NewsPanel.tsx \
  frontend/app/page.tsx
git commit -m "feat: music news panel on home page sourced from NewsAPI"
```

---

## Task 3: Trending themes section

**Goal:** Aggregate Claude's `themes` field across all stored interpretations and surface the top 5 on the home page. As users analyze more songs, this fills in.

**Files:**
- Modify: `backend/services/supabase.py`, `backend/routes/songs.py`, `backend/models/schemas.py`, `backend/tests/test_routes.py`
- Modify: `frontend/types/song.ts`, `frontend/lib/api.ts`, `frontend/app/page.tsx`
- Create: `frontend/components/TrendingThemes.tsx`

### 3A — Backend

- [ ] **Step 1: Add `get_trending_themes` to `backend/services/supabase.py`**

Append:
```python
def get_trending_themes(limit: int = 5) -> list[dict]:
    client = get_client()
    # Use Postgres RPC via raw SQL since the supabase-py client doesn't expose unnest()
    # Workaround: pull all interpretations and aggregate in Python. For an MVP-scale DB
    # this is fine; revisit if interpretations table grows past ~10k rows.
    result = client.table("interpretations").select("content").limit(10000).execute()
    counts: dict[str, int] = {}
    for row in result.data or []:
        themes = (row.get("content") or {}).get("themes") or []
        for theme in themes:
            if isinstance(theme, str) and theme.strip():
                key = theme.strip().lower()
                counts[key] = counts.get(key, 0) + 1
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return [{"theme": t, "count": c} for t, c in top]
```

- [ ] **Step 2: Add route in `backend/routes/songs.py`**

```python
@router.get("/trending/themes")
async def trending_themes(limit: int = Query(default=5, ge=1, le=20)):
    return supabase_service.get_trending_themes(limit)
```

- [ ] **Step 3: Add `TrendingTheme` to `backend/models/schemas.py`**

```python
class TrendingTheme(BaseModel):
    theme: str
    count: int
```

- [ ] **Step 4: Test in `backend/tests/test_routes.py`**

```python
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
```

Run: `pytest tests/ -q` — expected all PASS.

### 3B — Frontend

- [ ] **Step 5: Add `TrendingTheme` to `frontend/types/song.ts`**

```typescript
export interface TrendingTheme {
  theme: string;
  count: number;
}
```

- [ ] **Step 6: Add `getTrendingThemes` to `frontend/lib/api.ts`**

```typescript
export async function getTrendingThemes(limit = 5): Promise<TrendingTheme[]> {
  const res = await fetch(`${BASE_URL}/trending/themes?limit=${limit}`, { cache: 'no-store' });
  if (!res.ok) return [];
  return res.json();
}
```

Update the import line on `lib/api.ts` to add `TrendingTheme`.

- [ ] **Step 7: Create `frontend/components/TrendingThemes.tsx`**

```tsx
import Link from 'next/link';
import { TrendingTheme } from '@/types/song';

export default function TrendingThemes({ themes }: { themes: TrendingTheme[] }) {
  if (themes.length === 0) {
    return (
      <p className="text-neutral-500 text-sm">
        Analyze a few songs to see trending themes.
      </p>
    );
  }
  return (
    <div className="flex flex-wrap gap-2">
      {themes.map(t => (
        <Link
          key={t.theme}
          href={`/?q=${encodeURIComponent(t.theme)}`}
          className="bg-neutral-900 hover:bg-neutral-800 text-neutral-300 text-sm px-3 py-1.5 rounded-full transition-colors"
        >
          {t.theme}
          <span className="text-neutral-500 text-xs ml-2">{t.count}</span>
        </Link>
      ))}
    </div>
  );
}
```

- [ ] **Step 8: Mount TrendingThemes in `frontend/app/page.tsx`**

In the default (no query) branch, change the right sidebar to stack News + TrendingThemes:

```tsx
const [billboard, articles, themes] = await Promise.all([
  getBillboard(10),
  getMusicNews(8),
  getTrendingThemes(8),
]);
// ...
<aside className="space-y-10">
  <div>
    <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">
      Music News
    </h2>
    <NewsPanel articles={articles} />
  </div>
  <div>
    <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">
      Trending Themes
    </h2>
    <TrendingThemes themes={themes} />
  </div>
</aside>
```

Update imports to add `getTrendingThemes` and `TrendingThemes`.

- [ ] **Step 9: TypeScript check + commit**

```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/frontend && npx tsc --noEmit
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer
git add backend/services/supabase.py backend/routes/songs.py backend/models/schemas.py \
  backend/tests/test_routes.py \
  frontend/types/song.ts frontend/lib/api.ts \
  frontend/components/TrendingThemes.tsx frontend/app/page.tsx
git commit -m "feat: trending themes section on home page sidebar"
```

---

## Task 4: Featured artist banner

**Goal:** Top of the home page shows a colored "Featured" banner highlighting the Billboard #1 artist and their #1 song. No new backend — derived from the existing Billboard data on the page.

**Files:**
- Create: `frontend/components/FeaturedArtistBanner.tsx`
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Create `frontend/components/FeaturedArtistBanner.tsx`**

```tsx
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { BillboardSong, Song } from '@/types/song';
import { analyzeSong } from '@/lib/api';
import Spinner from '@/components/Spinner';

export default function FeaturedArtistBanner({ feature }: { feature: BillboardSong | null }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!feature) return null;

  async function handleListen() {
    if (loading) return;
    setLoading(true);
    setError(null);
    try {
      const song: Song = await analyzeSong(feature!.title, feature!.artist);
      sessionStorage.setItem(`song-${song.id}`, JSON.stringify(song));
      router.push(`/song/${song.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setLoading(false);
    }
  }

  return (
    <div className="relative overflow-hidden rounded-2xl mb-10 bg-gradient-to-br from-purple-900 via-neutral-900 to-neutral-950 p-8">
      <p className="text-xs font-bold text-purple-300 uppercase tracking-widest mb-2">
        Featured Today
      </p>
      <h2 className="text-4xl font-black text-white mb-1 leading-tight">{feature.artist}</h2>
      <p className="text-neutral-300 text-lg mb-4">
        <span className="text-neutral-500">Currently #1 with</span> {feature.title}
      </p>
      {error && <p className="text-red-400 text-xs mb-2">{error}</p>}
      <button
        onClick={handleListen}
        disabled={loading}
        className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white font-medium px-5 py-2 rounded-full transition-colors"
      >
        {loading ? <Spinner size="sm" /> : null}
        {loading ? 'Analyzing…' : 'Read the analysis →'}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Mount in `frontend/app/page.tsx`**

In the default branch, just above the 2-column grid, render the banner using `billboard[0]`:

```tsx
<FeaturedArtistBanner feature={billboard[0] ?? null} />
```

Update imports to add `FeaturedArtistBanner`.

- [ ] **Step 3: TypeScript check + commit**

```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/frontend && npx tsc --noEmit
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer
git add frontend/components/FeaturedArtistBanner.tsx frontend/app/page.tsx
git commit -m "feat: featured artist banner derived from Billboard #1"
```

---

## Task 5: Search redesign — Apple Music style + Albums category

**Goal:** Desktop shows Artists in a left sidebar, then Songs + Albums + Lyrics as separate panels in the main column. Albums are derived from songs already analyzed in our DB (so the section is empty initially and fills as more songs get analyzed). Mobile stacks.

**Files:**
- Modify: `backend/services/supabase.py`, `backend/services/genius.py`, `backend/routes/songs.py`, `backend/models/schemas.py`, `backend/tests/test_routes.py`
- Modify: `frontend/types/song.ts`, `frontend/components/SearchResultsList.tsx`, `frontend/app/page.tsx`

### 5A — Backend: derive albums from cached songs

- [ ] **Step 1: Add `search_cached_albums` to `backend/services/supabase.py`**

```python
def search_cached_albums(query: str, limit: int = 5) -> list[dict]:
    """Find albums by querying songs whose title or artist matches, then deduplicating by album_id."""
    client = get_client()
    pattern = f"%{query}%"
    # Search songs by title OR artist (case-insensitive), only those with metadata.album_id
    result = (
        client.table("songs")
        .select("metadata, artist")
        .or_(f"title.ilike.{pattern},artist.ilike.{pattern}")
        .not_.is_("metadata", "null")
        .limit(50)
        .execute()
    )
    seen: set[int] = set()
    albums: list[dict] = []
    for row in result.data or []:
        meta = row.get("metadata") or {}
        album_id = meta.get("album_id")
        album_name = meta.get("album_name")
        if not album_id or not album_name or album_id in seen:
            continue
        seen.add(album_id)
        albums.append({
            "album_id": album_id,
            "name": album_name,
            "artist": row.get("artist", ""),
            "thumbnail": meta.get("album_art_url"),
        })
        if len(albums) >= limit:
            break
    return albums
```

- [ ] **Step 2: Update `search_songs` in `backend/services/genius.py`**

The function currently returns `{songs, lyrics, artists}`. Update it to also accept and pass through an optional pre-computed `albums` list (we'll inject it in the route). Easier approach: keep `search_songs` unchanged and combine in the route.

- [ ] **Step 3: Update `/songs/search` route in `backend/routes/songs.py`**

Change the route to merge in cached albums:
```python
@router.get("/songs/search")
async def search_suggestions(q: str = Query(..., min_length=1, max_length=200)):
    genius_results = await genius_service.search_songs(q)
    albums = supabase_service.search_cached_albums(q, limit=5)
    return {**genius_results, "albums": albums}
```

- [ ] **Step 4: Add `AlbumSearchResult` to `backend/models/schemas.py`**

```python
class AlbumSearchResult(BaseModel):
    album_id: int
    name: str
    artist: str
    thumbnail: Optional[str] = None
```

- [ ] **Step 5: Add tests in `backend/tests/test_routes.py`**

```python
def test_songs_search_includes_albums_from_cache():
    genius_results = {"songs": [], "lyrics": [], "artists": []}
    albums = [{"album_id": 100, "name": "Album", "artist": "Artist", "thumbnail": None}]
    with patch("routes.songs.genius_service.search_songs", return_value=genius_results), \
         patch("routes.songs.supabase_service.search_cached_albums", return_value=albums):
        response = client.get("/songs/search?q=test")
    assert response.status_code == 200
    data = response.json()
    assert data["albums"][0]["name"] == "Album"
```

Update the existing `test_songs_search_returns_categorized_results` and `test_songs_search_returns_empty_categories_when_no_results` tests to also assert on `"albums"` field (just add `"albums": []` to the expected response).

Run: `pytest tests/ -q` — all PASS.

### 5B — Frontend types and layout

- [ ] **Step 6: Update `frontend/types/song.ts`**

```typescript
export interface AlbumSearchResult {
  album_id: number;
  name: string;
  artist: string;
  thumbnail: string | null;
}

export interface SearchResults {
  songs: SearchResult[];
  lyrics: SearchResult[];
  artists: ArtistResult[];
  albums: AlbumSearchResult[];
}
```

- [ ] **Step 7: Update `frontend/lib/api.ts`**

The empty default for `searchSongs` needs the new shape:
```typescript
const empty: SearchResults = { songs: [], lyrics: [], artists: [], albums: [] };
```

- [ ] **Step 8: Widen search results page**

In `frontend/app/page.tsx` change the search branch's `<main>` from `max-w-2xl` to `max-w-6xl`.

- [ ] **Step 9: Restructure `frontend/components/SearchResultsList.tsx`**

The current layout is a single column with three stacked sections. Restructure to:

```
Desktop (lg+):
┌─────────────┬───────────────────────────────────┐
│  ARTISTS    │  SONGS                            │
│  ┌────────┐ │  ┌──────────┐  ┌──────────┐      │
│  │ artist │ │  │ song     │  │ song     │      │
│  │ artist │ │  │ song     │  │ song     │      │
│  └────────┘ │  └──────────┘  └──────────┘      │
│             │                                   │
│             │  LYRICS                           │
│             │  ┌──────────┐  ┌──────────┐      │
│             │  │ lyric    │  │ lyric    │      │
└─────────────┴───────────────────────────────────┘

Mobile:
┌─────────────┐
│  ARTISTS    │
│  ┌────────┐ │
│  │ artist │ │
│  └────────┘ │
│  SONGS      │
│  ┌────────┐ │
│  │ song   │ │
│  └────────┘ │
│  LYRICS     │
└─────────────┘
```

Replace the existing component. Keep all existing logic for `handleSongSelect`, `handleArtistSelect`, `loadingId`, `error`, and the `isEmpty` check. Replace only the JSX structure of the return.

Key changes:
- Wrap in `<div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-8">`
- Left column = Artists (or hidden on mobile if no artists)
- Right column = Songs grid + Lyrics list

Updated return statement (keep the rest of the component as-is):
```tsx
return (
  <div>
    {error && <p className="text-red-400 text-xs mb-4">{error}</p>}

    <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-8">
      {/* Left sidebar — Artists */}
      {results.artists.length > 0 && (
        <div>
          <SectionHeader label="Artists" />
          <div className="space-y-2">
            {results.artists.map(a => (
              <ArtistRow
                key={a.artist_id}
                artist={a}
                onClick={() => handleArtistSelect(a)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Main column — Songs grid + Albums + Lyrics */}
      <div className={results.artists.length > 0 ? '' : 'lg:col-span-2'}>
        {results.songs.length > 0 && (
          <div>
            <SectionHeader label="Songs" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {results.songs.map(s => (
                <SongCard
                  key={s.genius_id}
                  result={s}
                  loading={loadingId === s.genius_id}
                  onClick={() => handleSongSelect(s)}
                />
              ))}
            </div>
          </div>
        )}

        {results.albums.length > 0 && (
          <div className="mt-8">
            <SectionHeader label="Albums" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {results.albums.map(a => (
                <AlbumCard key={a.album_id} album={a} />
              ))}
            </div>
          </div>
        )}

        {results.lyrics.length > 0 && (
          <div className="mt-8">
            <SectionHeader label="Lyrics" />
            <div className="space-y-2">
              {results.lyrics.map(s => (
                <SongRow
                  key={s.genius_id}
                  result={s}
                  loading={loadingId === s.genius_id}
                  onClick={() => handleSongSelect(s)}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  </div>
);
```

Add an `AlbumCard` component (since albums route to a different page, not analyze):
```tsx
import Link from 'next/link';
// ...

function AlbumCard({ album }: { album: AlbumSearchResult }) {
  return (
    <Link
      href={`/album/${album.album_id}`}
      className="flex items-center gap-4 bg-neutral-900 hover:bg-neutral-800 rounded-lg p-3 transition-colors"
    >
      {album.thumbnail ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={album.thumbnail}
          alt=""
          width={64}
          height={64}
          onError={(e) => { e.currentTarget.style.display = 'none'; }}
          className="w-16 h-16 rounded object-cover shrink-0"
        />
      ) : (
        <div className="w-16 h-16 rounded bg-neutral-700 shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-white font-semibold truncate">{album.name}</p>
        <p className="text-neutral-400 text-sm truncate">{album.artist}</p>
      </div>
    </Link>
  );
}
```

Also update the imports at the top of the file to include `AlbumSearchResult` and `Link`:
```tsx
import { SearchResults, SearchResult, ArtistResult, AlbumSearchResult, Song } from '@/types/song';
import Link from 'next/link';
```

And update the `isEmpty` check to consider the new field:
```tsx
const isEmpty =
  results.songs.length === 0 &&
  results.lyrics.length === 0 &&
  results.artists.length === 0 &&
  results.albums.length === 0;
```

- [ ] **Step 3: Add a new `SongCard` component (larger, grid-friendly)**

Inside the same file, add a `SongCard` component above `SearchResultsList`:

```tsx
function SongCard({
  result,
  loading,
  onClick,
}: {
  result: SearchResult;
  loading: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="flex items-center gap-4 bg-neutral-900 hover:bg-neutral-800 disabled:opacity-60 rounded-lg p-3 transition-colors text-left"
    >
      {result.thumbnail ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={result.thumbnail}
          alt=""
          width={64}
          height={64}
          className="w-16 h-16 rounded object-cover shrink-0"
        />
      ) : (
        <div className="w-16 h-16 rounded bg-neutral-700 shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-white font-semibold truncate">{result.title}</p>
        <p className="text-neutral-400 text-sm truncate">{result.artist}</p>
      </div>
      <div className="w-4 h-4 shrink-0 flex items-center justify-center">
        {loading && <Spinner size="sm" />}
      </div>
    </button>
  );
}
```

The original `SongRow` is still used in the Lyrics section (compact list style).

- [ ] **Step 4: TypeScript check**

```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/frontend
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/SearchResultsList.tsx frontend/app/page.tsx
git commit -m "feat: Apple Music-style search layout with artist sidebar and song card grid"
```

---

## Task 6: Album page

**Goal:** Each song's banner shows album name as a link. Clicking navigates to `/album/[id]` which shows basic album info — cover art, title, artist, release year, producer credits — and a clickable tracklist. No description/About section. Each track in the tracklist triggers analysis on click.

### 6A — Migration

- [ ] **Step 1: Create `backend/migrations/007_albums.sql`**

```sql
create table if not exists albums (
  id uuid primary key default gen_random_uuid(),
  genius_id integer unique,
  title text not null,
  artist text not null,
  release_year text,
  cover_art_url text,
  description text,
  tracklist jsonb,
  created_at timestamptz not null default now()
);

create index if not exists albums_genius_id_idx on albums(genius_id);
```

**Run this in Supabase SQL Editor before Task 4 tests against a real DB.** Unit tests mock Supabase and pass without the migration.

### 6B — Genius album fetcher

- [ ] **Step 2: Write failing test for `get_album_details`**

Add to `backend/tests/test_genius.py` (and add `get_album_details` to the import):
```python
@pytest.mark.asyncio
async def test_get_album_details_returns_album_with_tracklist_and_producers():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": {
            "album": {
                "id": 100,
                "name": "Certified Lover Boy",
                "artist": {"name": "Drake"},
                "release_date_for_display": "September 3, 2021",
                "cover_art_url": "https://images.genius.com/cover.jpg",
                "performance_groups": [
                    {"label": "Producer", "artists": [{"name": "Noah '40' Shebib"}, {"name": "Boi-1da"}]},
                    {"label": "Writer", "artists": [{"name": "Drake"}]},
                ],
            }
        }
    }
    mock_response.raise_for_status = MagicMock()

    # Mock both album fetch and tracks fetch
    track_response = MagicMock()
    track_response.json.return_value = {
        "response": {
            "songs": [
                {"id": 1, "title": "Champagne Poetry", "song_art_image_thumbnail_url": None},
                {"id": 2, "title": "Papi's Home", "song_art_image_thumbnail_url": None},
            ]
        }
    }
    track_response.raise_for_status = MagicMock()

    async def fake_get(url, **kwargs):
        if "/albums/" in url and "/tracks" not in url:
            return mock_response
        return track_response

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(side_effect=fake_get)
        result = await get_album_details(100)

    assert result["title"] == "Certified Lover Boy"
    assert result["artist"] == "Drake"
    assert result["release_year"] == "2021"
    assert result["cover_art_url"] == "https://images.genius.com/cover.jpg"
    assert result["producers"] == ["Noah '40' Shebib", "Boi-1da"]
    assert len(result["tracklist"]) == 2
    assert result["tracklist"][0]["title"] == "Champagne Poetry"


@pytest.mark.asyncio
async def test_get_album_details_returns_empty_producers_when_missing():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": {
            "album": {
                "id": 100,
                "name": "Album",
                "artist": {"name": "Artist"},
                "release_date_for_display": "2024",
                "cover_art_url": None,
                "performance_groups": [],
            }
        }
    }
    mock_response.raise_for_status = MagicMock()

    track_response = MagicMock()
    track_response.json.return_value = {"response": {"songs": []}}
    track_response.raise_for_status = MagicMock()

    async def fake_get(url, **kwargs):
        if "/tracks" in url:
            return track_response
        return mock_response

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(side_effect=fake_get)
        result = await get_album_details(100)

    assert result["producers"] == []


@pytest.mark.asyncio
async def test_get_album_details_returns_empty_dict_on_error():
    import httpx as _httpx
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=_httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())
        )
        result = await get_album_details(100)
    assert result == {}
```

- [ ] **Step 3: Add `get_album_details` to `backend/services/genius.py`**

```python
async def get_album_details(album_id: int) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            album_resp = await client.get(
                f"{GENIUS_API_BASE}/albums/{album_id}",
                params={"text_format": "plain"},
                headers={"Authorization": f"Bearer {settings.genius_access_token}"},
            )
            album_resp.raise_for_status()
            album = album_resp.json()["response"]["album"]

            tracks_resp = await client.get(
                f"{GENIUS_API_BASE}/albums/{album_id}/tracks",
                params={"text_format": "plain", "per_page": 50},
                headers={"Authorization": f"Bearer {settings.genius_access_token}"},
            )
            tracks_resp.raise_for_status()
            tracks_data = tracks_resp.json()["response"].get("songs", [])
    except (httpx.HTTPStatusError, httpx.RequestError):
        return {}

    release_date = album.get("release_date_for_display", "")
    year_match = re.search(r"\b(\d{4})\b", release_date) if release_date else None
    release_year = year_match.group(1) if year_match else None

    # Producers come from performance_groups with label "Producer"
    producers: list[str] = []
    for group in album.get("performance_groups") or []:
        if (group.get("label") or "").lower() == "producer":
            for artist in group.get("artists") or []:
                name = artist.get("name")
                if name and name not in producers:
                    producers.append(name)

    tracklist = [
        {
            "genius_id": t.get("id"),
            "title": t.get("title", ""),
            "thumbnail": t.get("song_art_image_thumbnail_url"),
        }
        for t in tracks_data
    ]

    return {
        "genius_id": album.get("id"),
        "title": album.get("name", ""),
        "artist": (album.get("artist") or {}).get("name", ""),
        "release_year": release_year,
        "cover_art_url": album.get("cover_art_url"),
        "producers": producers,
        "tracklist": tracklist,
    }
```

- [ ] **Step 4: Update `get_song_details` to include `album_id`**

In the existing function, change the return to also include `album.get("id")`:
```python
    return {
        "album_id": album.get("id"),
        "album_art_url": song.get("song_art_image_url"),
        "album_name": album.get("name"),
        "release_year": release_year,
        "producer": producer,
    }
```

Update the existing test `test_get_song_details_returns_metadata` to assert `result["album_id"]` is whatever the mock returns. Add `"id": 999` to the mock album object and assert `result["album_id"] == 999`.

- [ ] **Step 5: Run genius tests**

```bash
pytest tests/test_genius.py -q
```
Expected: all PASS.

### 4C — Supabase album functions

- [ ] **Step 6: Add `find_album`, `store_album`, `get_album_by_id` to `backend/services/supabase.py`**

```python
def find_album(genius_album_id: int) -> Optional[dict]:
    client = get_client()
    result = (
        client.table("albums")
        .select("*")
        .eq("genius_id", genius_album_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def store_album(album_data: dict) -> dict:
    client = get_client()
    result = client.table("albums").insert(album_data).execute()
    return result.data[0]


def get_album_by_id(album_id: str) -> Optional[dict]:
    client = get_client()
    result = (
        client.table("albums")
        .select("*")
        .eq("id", album_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None
```

### 4D — Album schemas

- [ ] **Step 7: Update `backend/models/schemas.py`**

Add `album_id` to `SongMetadata`:
```python
class SongMetadata(BaseModel):
    album_id: Optional[int] = None
    album_art_url: Optional[str] = None
    album_name: Optional[str] = None
    release_year: Optional[str] = None
    producer: Optional[str] = None
```

Add new models:
```python
class AlbumTrack(BaseModel):
    genius_id: Optional[int] = None
    title: str
    thumbnail: Optional[str] = None


class AlbumResponse(BaseModel):
    id: str
    genius_id: Optional[int] = None
    title: str
    artist: str
    release_year: Optional[str] = None
    cover_art_url: Optional[str] = None
    producers: list[str] = []
    tracklist: list[AlbumTrack] = []
```

### 4E — Album route

- [ ] **Step 8: Add `GET /album/{album_id}` to `backend/routes/songs.py`**

Add a helper inside `routes/songs.py`:
```python
async def _resolve_album(album_id: str) -> Optional[dict]:
    # First try a UUID lookup (our DB id)
    by_uuid = supabase_service.get_album_by_id(album_id)
    if by_uuid:
        return by_uuid

    # Then try as a Genius integer id — fetch from Genius and cache
    try:
        genius_id_int = int(album_id)
    except ValueError:
        return None

    cached = supabase_service.find_album(genius_id_int)
    if cached:
        return cached

    fetched = await genius_service.get_album_details(genius_id_int)
    if not fetched:
        return None

    return supabase_service.store_album(fetched)
```

Add at top: `from typing import Optional`

Append route:
```python
@router.get("/album/{album_id}")
async def get_album(album_id: str):
    album = await _resolve_album(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    return album
```

This route accepts either a Supabase UUID or a Genius integer ID — the frontend will pass Genius IDs from song banners (since that's what's stored in song metadata).

- [ ] **Step 9: Tests for the album route**

In `backend/tests/test_routes.py`:
```python
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
```

Run all backend tests: `pytest tests/ -q` — expected all PASS.

### 4F — Frontend types and API

- [ ] **Step 10: Update `frontend/types/song.ts`**

Add `album_id` to `SongMetadata`:
```typescript
export interface SongMetadata {
  album_id: number | null;
  album_art_url: string | null;
  album_name: string | null;
  release_year: string | null;
  producer: string | null;
}
```

Add new types:
```typescript
export interface AlbumTrack {
  genius_id: number | null;
  title: string;
  thumbnail: string | null;
}

export interface Album {
  id: string;
  genius_id: number | null;
  title: string;
  artist: string;
  release_year: string | null;
  cover_art_url: string | null;
  producers: string[];
  tracklist: AlbumTrack[];
}
```

- [ ] **Step 11: Add `getAlbumById` to `frontend/lib/api.ts`**

Update import line to include `Album`. Append:
```typescript
export async function getAlbumById(albumId: string | number): Promise<Album | null> {
  const res = await fetch(`${BASE_URL}/album/${albumId}`, { cache: 'no-store' });
  if (!res.ok) return null;
  return res.json();
}
```

### 4G — SongBanner: clickable album link

- [ ] **Step 12: Update `frontend/components/SongBanner.tsx`**

The "Album" pill in the metadata row should be a `<Link>` to `/album/{album_id}` when `album_id` is present, otherwise a plain `<span>`.

Add import at top:
```tsx
import Link from 'next/link';
```

Change the Album rendering from:
```tsx
{meta?.album_name && (
  <span><span className="text-neutral-500">Album</span> {meta.album_name}</span>
)}
```
to:
```tsx
{meta?.album_name && (
  meta.album_id ? (
    <Link href={`/album/${meta.album_id}`} className="hover:text-purple-300 transition-colors">
      <span className="text-neutral-500">Album</span> {meta.album_name}
    </Link>
  ) : (
    <span><span className="text-neutral-500">Album</span> {meta.album_name}</span>
  )
)}
```

### 4H — Album page and components

- [ ] **Step 13: Create `frontend/components/AlbumBanner.tsx`**

```tsx
import { Album } from '@/types/song';

export default function AlbumBanner({ album }: { album: Album }) {
  const cover = album.cover_art_url;
  return (
    <div className="relative overflow-hidden rounded-xl mb-8 min-h-48">
      {cover && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={cover}
          alt=""
          aria-hidden
          className="absolute inset-0 w-full h-full object-cover scale-110 blur-2xl opacity-50"
        />
      )}
      <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/50 to-neutral-950" />
      <div className="relative z-10 flex gap-6 p-6 items-end">
        {cover && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={cover}
            alt={`${album.title} cover`}
            width={140}
            height={140}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
            className="rounded-lg shadow-2xl shrink-0 hidden sm:block"
          />
        )}
        <div className="min-w-0">
          <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest mb-1">Album</p>
          <h1 className="text-3xl font-black text-white leading-tight">{album.title}</h1>
          <p className="text-neutral-300 text-lg mt-1">{album.artist}</p>
          <div className="flex flex-wrap gap-x-6 gap-y-1 mt-3 text-xs text-neutral-400">
            {album.release_year && (
              <span><span className="text-neutral-500">Year</span> {album.release_year}</span>
            )}
            {album.producers.length > 0 && (
              <span><span className="text-neutral-500">Produced by</span> {album.producers.join(', ')}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

If the AlbumBanner uses an `onError` handler on the `<img>`, it must be a client component. Add `'use client';` at the top of the file.

- [ ] **Step 14: Create `frontend/components/Tracklist.tsx`**

```tsx
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { AlbumTrack, Song } from '@/types/song';
import { analyzeSong } from '@/lib/api';
import Spinner from '@/components/Spinner';

export default function Tracklist({
  tracks,
  artist,
}: {
  tracks: AlbumTrack[];
  artist: string;
}) {
  const router = useRouter();
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (tracks.length === 0) {
    return <p className="text-neutral-500 text-sm">No tracks listed.</p>;
  }

  async function handleSelect(track: AlbumTrack) {
    if (!track.genius_id || loadingId !== null) return;
    setLoadingId(track.genius_id);
    setError(null);
    try {
      const song: Song = await analyzeSong(track.title, artist);
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
      <ol className="space-y-1">
        {tracks.map((track, i) => (
          <li key={track.genius_id ?? i}>
            <button
              onClick={() => handleSelect(track)}
              disabled={!!loadingId}
              className="w-full flex items-center gap-4 hover:bg-neutral-800 disabled:opacity-60 rounded px-3 py-2 transition-colors text-left"
            >
              <span className="text-neutral-600 font-medium w-6 text-right text-sm shrink-0">
                {i + 1}
              </span>
              <span className="text-white text-sm flex-1 min-w-0 truncate">{track.title}</span>
              <div className="w-4 h-4 shrink-0 flex items-center justify-center">
                {loadingId === track.genius_id && <Spinner size="sm" />}
              </div>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
```

- [ ] **Step 15: Create `frontend/app/album/[id]/page.tsx`**

```tsx
import { getAlbumById } from '@/lib/api';
import AlbumBanner from '@/components/AlbumBanner';
import Tracklist from '@/components/Tracklist';

export default async function AlbumPage({ params }: { params: { id: string } }) {
  const album = await getAlbumById(params.id);

  if (!album) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-8">
        <p className="text-red-400 text-sm">Album not found.</p>
      </main>
    );
  }

  return (
    <main className="max-w-3xl mx-auto px-6 py-8">
      <AlbumBanner album={album} />

      <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">
        Tracks
      </h2>
      <Tracklist tracks={album.tracklist} artist={album.artist} />
    </main>
  );
}
```

- [ ] **Step 16: TypeScript check**

```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/frontend
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 17: Commit**

```bash
git add backend/migrations/007_albums.sql \
  backend/services/genius.py backend/services/supabase.py \
  backend/routes/songs.py backend/models/schemas.py \
  backend/tests/test_genius.py backend/tests/test_routes.py \
  frontend/types/song.ts frontend/lib/api.ts \
  frontend/components/SongBanner.tsx \
  frontend/components/AlbumBanner.tsx frontend/components/Tracklist.tsx \
  frontend/app/album/
git commit -m "feat: album pages with tracklist, producer credits, and SongBanner album link"
```

---

## Final: push

```bash
git push
```

---

## Notes

- **NewsAPI key**: Required before Task 2 will return real news. Get a free Developer key at https://newsapi.org/register and add to `backend/.env` as `NEWSAPI_KEY=<key>`. Without it, `/news` returns `[]` and the home page shows "News feed unavailable." Free tier is 100 requests/day; with 1h cache that's ~24/day from the backend (plenty of headroom).
- **Migration 007** must be run in Supabase SQL Editor before album page works against real DB. Unit tests pass without it.
- **Genius album API**: Two calls per uncached album (album details + tracks). Cached on first fetch, so subsequent views are fast.
- **Album tracklist analyze**: Clicking a track triggers `POST /analyze` for that track. First click on a track takes 10–20s for AI; subsequent loads use the cached interpretation.
- **Cached song `album_id` backfill**: Songs analyzed before this change have `metadata.album_id` missing. The Album pill in their banner will be a plain span (not clickable). Re-analyzing the song fills in `album_id`.
- **Pre-warm cache**: Runs as a background task at startup so boot isn't blocked. If Billboard is down at startup, the cache fills on first user request.
