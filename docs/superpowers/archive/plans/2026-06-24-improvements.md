# Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ten improvements across backend and frontend — Billboard chart, TL;DR, song metadata banner, UI polish, and several bug fixes.

**Architecture:** Five independent tasks in dependency order. Tasks 1–2 touch no schema. Task 3 adds a DB column. Task 4 adds a backend service + DB column. Task 5 adds an AI schema field. All tasks commit individually.

**Tech Stack:** FastAPI, Python, Next.js 14, TypeScript, Tailwind CSS, Supabase, billboard.py (new dep), Pillow not needed (CSS blur approach for banner).

---

## File Map

### Backend

| File | Change |
|---|---|
| `backend/services/genius.py` | Add `get_song_details(genius_id)` |
| `backend/services/billboard.py` | Create — Billboard Hot 100 scraper with 24h in-memory cache |
| `backend/services/discourse.py` | Swap fetch order: Genius first, YouTube second |
| `backend/services/anthropic.py` | Add `tldr` to prompt + `REQUIRED_KEYS` |
| `backend/routes/songs.py` | Add `GET /songs/billboard`; wire metadata into analyze route |
| `backend/models/schemas.py` | Add `tldr` to `InterpretationContent`; add `metadata` to `SongResponse` |
| `backend/migrations/006_song_metadata.sql` | Add `metadata JSONB` column to songs |
| `backend/requirements.txt` | Add `billboard.py` |
| `backend/tests/test_routes.py` | Add billboard + metadata tests |
| `backend/tests/test_genius.py` | Add `get_song_details` tests |
| `backend/tests/test_anthropic.py` | Add `tldr` field test |
| `backend/services/supabase.py` | Update `store_song` to accept metadata; `get_trending` renamed label only |

### Frontend

| File | Change |
|---|---|
| `frontend/types/song.ts` | Add `SongMetadata`, `BillboardSong`; update `Song.interpretation.tldr?`, `Song.metadata?` |
| `frontend/lib/api.ts` | Add `getBillboard()` |
| `frontend/components/Spinner.tsx` | Create — reusable loading spinner |
| `frontend/components/BillboardChart.tsx` | Create — Billboard top 10 with analyze-on-click |
| `frontend/components/SongBanner.tsx` | Create — album art blurred background banner |
| `frontend/components/AnalysisPanel.tsx` | TL;DR default view + expand; reorder community sources |
| `frontend/components/BreakdownCard.tsx` | "Claude on this line" → "Lyriq on this line" |
| `frontend/components/SearchResultsList.tsx` | Upgrade text "Analyzing…" to `<Spinner>` |
| `frontend/components/TrendingChart.tsx` | "plays" → "views" |
| `frontend/app/layout.tsx` | Update metadata description |
| `frontend/app/page.tsx` | Replace TrendingChart with BillboardChart |
| `frontend/app/song/[id]/page.tsx` | Add SongBanner; analysis panel background; loading throbber |

---

## Task 1: Quick fixes — boilerplate, ordering, copy, labels

**Files:**
- Modify: `backend/services/genius.py` (normalize_lyrics)
- Modify: `backend/services/discourse.py` (ordering)
- Modify: `frontend/components/BreakdownCard.tsx`
- Modify: `frontend/components/TrendingChart.tsx`
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/app/page.tsx`

### 1A — Fix lyrics boilerplate stripping

- [ ] **Step 1: Write a failing test for the contributor/translation line**

In `backend/tests/test_genius.py`, add:
```python
def test_normalize_lyrics_strips_contributor_and_translation_header():
    raw = "67 ContributorsTranslationsFrançaisItalianoSlap The City Lyrics\nYeah\nSlap the city"
    result = normalize_lyrics(raw)
    assert "Contributors" not in result
    assert "Français" not in result
    assert "Lyrics" not in result
    assert "Yeah" in result


def test_normalize_lyrics_strips_song_title_lyrics_line():
    raw = "Bohemian Rhapsody Lyrics\nIs this the real life?"
    result = normalize_lyrics(raw)
    assert "Bohemian Rhapsody Lyrics" not in result
    assert "Is this the real life?" in result
```

Run: `pytest tests/test_genius.py::test_normalize_lyrics_strips_contributor_and_translation_header tests/test_genius.py::test_normalize_lyrics_strips_song_title_lyrics_line -v`
Expected: FAIL

- [ ] **Step 2: Update `normalize_lyrics` in `backend/services/genius.py`**

Replace the existing `normalize_lyrics` function:
```python
def normalize_lyrics(lyrics: str) -> str:
    # Strip "67 ContributorsTranslationsFrançais...Song Title Lyrics" boilerplate line
    cleaned = re.sub(r"\d+\s*Contributor[^\n]*\n?", "", lyrics)
    # Strip any standalone "X Lyrics" line (e.g. "Slap The City Lyrics")
    cleaned = re.sub(r"^.+\bLyrics\s*$", "", cleaned, flags=re.MULTILINE)
    # Strip section headers like [Verse 1]
    cleaned = re.sub(r"\[.*?\]", "", cleaned)
    # Collapse excess blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
```

- [ ] **Step 3: Run tests to confirm they pass**

```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/backend
pytest tests/test_genius.py -v
```
Expected: all PASS (including 2 new ones).

### 1B — Genius annotations before YouTube comments

- [ ] **Step 4: Swap fetch order in `backend/services/discourse.py`**

Find `fetch_discourse` and change:
```python
async def fetch_discourse(genius_id: Optional[int], title: str, artist: str) -> list[dict]:
    excerpts = []
    excerpts.extend(await _fetch_youtube_comments(title, artist))
    if genius_id is not None:
        excerpts.extend(await _fetch_genius_annotations(genius_id))
    return excerpts
```
To:
```python
async def fetch_discourse(genius_id: Optional[int], title: str, artist: str) -> list[dict]:
    excerpts = []
    if genius_id is not None:
        excerpts.extend(await _fetch_genius_annotations(genius_id))
    excerpts.extend(await _fetch_youtube_comments(title, artist))
    return excerpts
```

Also update the `AnalysisPanel.tsx` community sort to pin Genius first at render time (defensive, since stored data may have old ordering). In `frontend/components/AnalysisPanel.tsx`, in the `commentary.map(...)` block, before mapping sort the list:
```tsx
const sortedCommentary = [...commentary].sort((a, b) => {
  if (a.source === 'genius' && b.source !== 'genius') return -1;
  if (b.source === 'genius' && a.source !== 'genius') return 1;
  return 0;
});
```
Then map `sortedCommentary` instead of `commentary`.

### 1C — "Claude" → "Lyriq" copy changes

- [ ] **Step 5: Update copy in three frontend files**

`frontend/components/BreakdownCard.tsx` line 7:
```tsx
// change:
Claude on this line
// to:
Lyriq on this line
```

`frontend/app/layout.tsx` line 10:
```tsx
// change:
description: 'Claude-powered song interpretation',
// to:
description: 'Lyriq — AI-powered song interpretation',
```

`frontend/app/page.tsx` line 30:
```tsx
// change:
Search a song to get Claude&apos;s interpretation of the lyrics.
// to:
Search a song to get Lyriq&apos;s interpretation of the lyrics.
```

### 1D — "plays" → "views"

- [ ] **Step 6: Update TrendingChart label**

In `frontend/components/TrendingChart.tsx`, change:
```tsx
{song.request_count.toLocaleString()} plays
```
to:
```tsx
{song.request_count.toLocaleString()} views
```

### 1E — Verify TypeScript and run all tests

- [ ] **Step 7: TypeScript check**
```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/frontend
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 8: Run all backend tests**
```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/backend
pytest tests/ -q
```
Expected: all PASS.

- [ ] **Step 9: Commit**
```bash
git add backend/services/genius.py backend/services/discourse.py \
  backend/tests/test_genius.py \
  frontend/components/BreakdownCard.tsx frontend/components/TrendingChart.tsx \
  frontend/app/layout.tsx frontend/app/page.tsx \
  frontend/components/AnalysisPanel.tsx
git commit -m "fix: strip lyrics boilerplate, Genius-first community order, Lyriq copy, views label"
```

---

## Task 2: UI polish — loading throbber + analysis panel background

**Files:**
- Create: `frontend/components/Spinner.tsx`
- Modify: `frontend/components/SearchResultsList.tsx`
- Modify: `frontend/app/song/[id]/page.tsx`

### 2A — Spinner component

- [ ] **Step 1: Create `frontend/components/Spinner.tsx`**

```tsx
export default function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const dims = size === 'sm' ? 'w-4 h-4' : size === 'lg' ? 'w-10 h-10' : 'w-6 h-6';
  return (
    <svg
      className={`${dims} animate-spin text-purple-400`}
      viewBox="0 0 24 24"
      fill="none"
      aria-label="Loading"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
```

### 2B — Use Spinner in SearchResultsList

- [ ] **Step 2: Replace "Analyzing…" text in `SearchResultsList.tsx`**

Add import at top:
```tsx
import Spinner from '@/components/Spinner';
```

In `SongRow`, change the loading indicator from:
```tsx
{loading && <span className="text-purple-400 text-xs shrink-0">Analyzing…</span>}
```
to:
```tsx
{loading && <Spinner size="sm" />}
```

### 2C — Song page: loading throbber + analysis panel background

- [ ] **Step 3: Update `frontend/app/song/[id]/page.tsx`**

Add import:
```tsx
import Spinner from '@/components/Spinner';
```

Replace the loading state:
```tsx
// change:
if (loading) {
  return <div className="text-neutral-400 p-12 text-sm">Analyzing lyrics...</div>;
}
// to:
if (loading) {
  return (
    <div className="flex items-center gap-3 p-12 text-neutral-400 text-sm">
      <Spinner />
      <span>Analyzing lyrics…</span>
    </div>
  );
}
```

Give the analysis panel column a distinct background so users can see it's independently scrollable:
```tsx
// change:
<div className="w-full lg:w-80 shrink-0 lg:sticky lg:top-6 lg:max-h-[calc(100vh-5rem)] lg:overflow-y-auto">
// to:
<div className="w-full lg:w-80 shrink-0 lg:sticky lg:top-6 lg:max-h-[calc(100vh-5rem)] lg:overflow-y-auto bg-neutral-900 rounded-xl p-5">
```

- [ ] **Step 4: TypeScript check**
```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/frontend
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 5: Commit**
```bash
git add frontend/components/Spinner.tsx frontend/components/SearchResultsList.tsx \
  "frontend/app/song/[id]/page.tsx"
git commit -m "feat: add loading spinner, distinct analysis panel background"
```

---

## Task 3: TL;DR — AI-generated summary field

**Files:**
- Modify: `backend/services/anthropic.py`
- Modify: `backend/models/schemas.py`
- Modify: `backend/tests/test_anthropic.py`
- Modify: `frontend/types/song.ts`
- Modify: `frontend/components/AnalysisPanel.tsx`

### 3A — Backend schema + prompt

- [ ] **Step 1: Write a failing test for `tldr` in `backend/tests/test_anthropic.py`**

Find the existing test that checks returned keys (look for a test asserting on interpretation structure). Add:
```python
@pytest.mark.asyncio
async def test_generate_interpretation_includes_tldr():
    valid_response = json.dumps({
        "tldr": "A song about betrayal and moving on.",
        "overall_meaning": "This song explores the themes of...",
        "emotional_tone": "melancholic",
        "themes": ["loss", "betrayal"],
        "key_lyric_breakdowns": [{"lyric": "test line", "breakdown": "means this"}],
    })
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=valid_response)]

    with patch("services.anthropic.anthropic.AsyncAnthropic") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value = mock_instance
        mock_instance.messages.create = AsyncMock(return_value=mock_response)
        result, model = await generate_interpretation("Song", "Artist", "lyrics here")

    assert "tldr" in result
    assert result["tldr"] == "A song about betrayal and moving on."
```

Run: `pytest tests/test_anthropic.py::test_generate_interpretation_includes_tldr -v`
Expected: FAIL (tldr not in REQUIRED_KEYS yet).

- [ ] **Step 2: Update `backend/services/anthropic.py`**

Change `REQUIRED_KEYS`:
```python
REQUIRED_KEYS = {"tldr", "overall_meaning", "emotional_tone", "themes", "key_lyric_breakdowns"}
```

Update `SYSTEM_PROMPT` — add `tldr` as the first field:
```python
SYSTEM_PROMPT = """You are a music critic and literary analyst. Analyze the provided song lyrics and return a JSON object with exactly these fields:
- tldr: 1-2 sentences — the most essential thing to understand about this song. Plain language, no jargon.
- overall_meaning: 2-3 paragraphs interpreting the song's central message and narrative
- emotional_tone: a brief phrase describing the emotional character (e.g. "melancholic and introspective")
- themes: a list of 3-6 theme strings (e.g. ["loss", "memory", "identity"])
- key_lyric_breakdowns: a list of objects, each with "lyric" (a quoted fragment) and "breakdown" (explanation of its significance)

Return ONLY valid JSON. No markdown fences, no explanation outside the JSON object."""
```

- [ ] **Step 3: Update `backend/models/schemas.py`**

In `InterpretationContent`, add `tldr` as optional (so existing stored songs still parse):
```python
class InterpretationContent(BaseModel):
    tldr: Optional[str] = None
    overall_meaning: str
    emotional_tone: str
    themes: list[str]
    key_lyric_breakdowns: list[LyricBreakdown]
```

Add `from typing import Optional` if not already imported (it is).

- [ ] **Step 4: Run tests**
```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/backend
pytest tests/ -q
```
Expected: all PASS.

### 3B — Frontend TL;DR UI

- [ ] **Step 5: Update `frontend/types/song.ts`**

In `Interpretation` interface, add the optional field:
```typescript
export interface Interpretation {
  tldr?: string;
  overall_meaning: string;
  emotional_tone: string;
  themes: string[];
  key_lyric_breakdowns: LyricBreakdown[];
}
```

- [ ] **Step 6: Update `frontend/components/AnalysisPanel.tsx` to show TL;DR**

Replace the "Overall meaning" section with a two-mode display:

```tsx
{/* TL;DR / Overall meaning */}
<div>
  <div className="flex items-center justify-between mb-2">
    <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest">
      {interpretation.tldr && !summaryExpanded ? 'TL;DR' : 'Meaning'}
    </p>
    {interpretation.tldr && (
      <button
        onClick={() => setSummaryExpanded(v => !v)}
        aria-expanded={summaryExpanded}
        aria-label={summaryExpanded ? 'Show brief summary' : 'Show full analysis'}
        className="text-purple-400 text-xs hover:underline"
      >
        {summaryExpanded ? 'TL;DR ↑' : 'Full analysis ↓'}
      </button>
    )}
  </div>

  {interpretation.tldr && !summaryExpanded ? (
    <p className="text-neutral-200 text-sm leading-relaxed font-medium">
      {interpretation.tldr}
    </p>
  ) : (
    <>
      <p className="text-neutral-300 text-sm leading-relaxed">
        {interpretation.overall_meaning}
      </p>
      {!interpretation.tldr && (
        /* Fallback for old songs without tldr: keep old truncation behavior */
        null
      )}
    </>
  )}
</div>
```

Remove the old `truncated`/`summaryExpanded` logic that was used for character-count truncation. The new logic replaces it entirely.

Note: for songs that have no `tldr` (existing songs), the component falls back to showing `overall_meaning` directly with no toggle.

- [ ] **Step 7: TypeScript check**
```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/frontend
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 8: Commit**
```bash
git add backend/services/anthropic.py backend/models/schemas.py \
  backend/tests/test_anthropic.py \
  frontend/types/song.ts frontend/components/AnalysisPanel.tsx
git commit -m "feat: add AI-generated tldr field with expand to full analysis"
```

---

## Task 4: Billboard Hot 100 on home page

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/services/billboard.py`
- Modify: `backend/routes/songs.py`
- Modify: `backend/tests/test_routes.py`
- Add: `frontend/types/song.ts` (BillboardSong)
- Modify: `frontend/lib/api.ts`
- Create: `frontend/components/BillboardChart.tsx`
- Modify: `frontend/app/page.tsx`

### 4A — Backend

- [ ] **Step 1: Add `billboard.py` to requirements**

Append to `backend/requirements.txt`:
```
billboard.py==3.2.0
```

Install locally:
```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/backend
pip install billboard.py
```

- [ ] **Step 2: Write failing route test**

In `backend/tests/test_routes.py`, add:
```python
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
```

Run: `pytest tests/test_routes.py -k "billboard" -v`
Expected: FAIL (route does not exist).

- [ ] **Step 3: Create `backend/services/billboard.py`**

```python
import asyncio
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

_cache: dict = {"data": None, "fetched_at": None}
_CACHE_TTL = timedelta(hours=24)


def get_hot_100(limit: int = 10) -> list[dict]:
    now = datetime.now(timezone.utc)
    if (
        _cache["data"] is not None
        and _cache["fetched_at"] is not None
        and now - _cache["fetched_at"] < _CACHE_TTL
    ):
        return _cache["data"][:limit]

    try:
        import billboard  # type: ignore
        chart = billboard.ChartData("hot-100")
        results = [
            {"rank": i + 1, "title": entry.title, "artist": entry.artist}
            for i, entry in enumerate(chart[:limit])
        ]
        _cache["data"] = results
        _cache["fetched_at"] = now
        return results
    except Exception as exc:
        logger.warning("Billboard fetch failed: %s", exc)
        return _cache["data"][:limit] if _cache["data"] else []
```

- [ ] **Step 4: Add route to `backend/routes/songs.py`**

Add import at top:
```python
import services.billboard as billboard_service
```

Append route:
```python
@router.get("/songs/billboard")
async def billboard_chart(limit: int = Query(default=10, ge=1, le=100)):
    return await asyncio.to_thread(billboard_service.get_hot_100, limit)
```

Add `import asyncio` at top if not already present.

- [ ] **Step 5: Run route tests**
```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/backend
pytest tests/ -q
```
Expected: all PASS.

### 4B — Frontend

- [ ] **Step 6: Add `BillboardSong` type to `frontend/types/song.ts`**

```typescript
export interface BillboardSong {
  rank: number;
  title: string;
  artist: string;
}
```

- [ ] **Step 7: Add `getBillboard()` to `frontend/lib/api.ts`**

```typescript
import { Song, TrendingSong, SearchResults, BillboardSong } from '@/types/song';

export async function getBillboard(limit = 10): Promise<BillboardSong[]> {
  const res = await fetch(`${BASE_URL}/songs/billboard?limit=${limit}`, {
    cache: 'no-store',
  });
  if (!res.ok) return [];
  return res.json();
}
```

- [ ] **Step 8: Create `frontend/components/BillboardChart.tsx`**

```tsx
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { BillboardSong, Song } from '@/types/song';
import { analyzeSong } from '@/lib/api';
import Spinner from '@/components/Spinner';

export default function BillboardChart({ songs }: { songs: BillboardSong[] }) {
  const router = useRouter();
  const [loadingKey, setLoadingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (songs.length === 0) {
    return (
      <p className="text-neutral-500 text-sm">
        Billboard chart unavailable. Search for a song above.
      </p>
    );
  }

  async function handleSelect(song: BillboardSong) {
    const key = `${song.title}-${song.artist}`;
    if (loadingKey) return;
    setLoadingKey(key);
    setError(null);
    try {
      const result: Song = await analyzeSong(song.title, song.artist);
      sessionStorage.setItem(`song-${result.id}`, JSON.stringify(result));
      router.push(`/song/${result.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setLoadingKey(null);
    }
  }

  return (
    <div>
      {error && <p className="text-red-400 text-xs mb-3">{error}</p>}
      <ol className="space-y-2">
        {songs.map(song => {
          const key = `${song.title}-${song.artist}`;
          const isLoading = loadingKey === key;
          return (
            <li key={key}>
              <button
                onClick={() => handleSelect(song)}
                disabled={!!loadingKey}
                className="w-full flex items-center gap-4 bg-neutral-900 hover:bg-neutral-800 disabled:opacity-60 rounded-lg px-4 py-3 transition-colors text-left"
              >
                <span className="text-neutral-600 font-bold w-5 text-right text-sm shrink-0">
                  {song.rank}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-white font-semibold truncate">{song.title}</p>
                  <p className="text-neutral-400 text-sm truncate">{song.artist}</p>
                </div>
                {isLoading && <Spinner size="sm" />}
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
```

- [ ] **Step 9: Update `frontend/app/page.tsx` to use BillboardChart**

Replace the entire file:
```tsx
import { getBillboard, searchSongs } from '@/lib/api';
import BillboardChart from '@/components/BillboardChart';
import SearchResultsList from '@/components/SearchResultsList';

export default async function HomePage({
  searchParams,
}: {
  searchParams: { q?: string };
}) {
  const query = searchParams.q?.trim() ?? '';

  if (query) {
    const results = await searchSongs(query);
    return (
      <main className="max-w-2xl mx-auto px-6 py-12">
        <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-1">
          Search results
        </p>
        <h1 className="text-2xl font-black text-white mb-8">&ldquo;{query}&rdquo;</h1>
        <SearchResultsList results={results} />
      </main>
    );
  }

  const billboard = await getBillboard(10);
  return (
    <main className="max-w-2xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-black text-white mb-2">What does it mean?</h1>
      <p className="text-neutral-400 mb-10">
        Search a song to get Lyriq&apos;s interpretation of the lyrics.
      </p>
      <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">
        Billboard Hot 100
      </h2>
      <BillboardChart songs={billboard} />
    </main>
  );
}
```

- [ ] **Step 10: TypeScript check**
```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/frontend
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 11: Commit**
```bash
git add backend/requirements.txt backend/services/billboard.py backend/routes/songs.py \
  backend/tests/test_routes.py \
  frontend/types/song.ts frontend/lib/api.ts \
  frontend/components/BillboardChart.tsx frontend/app/page.tsx
git commit -m "feat: Billboard Hot 100 replaces trending on home page, clickable to analyze"
```

---

## Task 5: Song page banner — album art, metadata, blurred color background

**Files:**
- Create: `backend/migrations/006_song_metadata.sql`
- Modify: `backend/services/genius.py` (add `get_song_details`)
- Modify: `backend/services/supabase.py` (update `store_song` to accept metadata)
- Modify: `backend/routes/songs.py` (fetch + store metadata in analyze flow)
- Modify: `backend/models/schemas.py` (add `metadata` to `SongResponse`)
- Modify: `backend/tests/test_genius.py` (add `get_song_details` test)
- Modify: `backend/tests/test_routes.py` (metadata in analyze response)
- Modify: `frontend/types/song.ts` (add `SongMetadata`, update `Song`)
- Create: `frontend/components/SongBanner.tsx`
- Modify: `frontend/app/song/[id]/page.tsx`

### 5A — Migration

- [ ] **Step 1: Create migration**

Create `backend/migrations/006_song_metadata.sql`:
```sql
alter table songs add column if not exists metadata jsonb;
```

**Run this in the Supabase dashboard → SQL Editor before proceeding.**

### 5B — Backend: Genius song details

- [ ] **Step 2: Write failing test in `backend/tests/test_genius.py`**

Add import at top: `from services.genius import search_song, fetch_lyrics, normalize_lyrics, get_song_details`

Add test:
```python
@pytest.mark.asyncio
async def test_get_song_details_returns_metadata():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": {
            "song": {
                "song_art_image_url": "https://images.genius.com/art.jpg",
                "album": {"name": "Certified Lover Boy", "release_date_for_display": "September 3, 2021"},
                "producer_artists": [{"name": "Noah '40' Shebib"}],
            }
        }
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await get_song_details(12345)

    assert result["album_art_url"] == "https://images.genius.com/art.jpg"
    assert result["album_name"] == "Certified Lover Boy"
    assert result["release_year"] == "2021"
    assert result["producer"] == "Noah '40' Shebib"
```

Run: `pytest tests/test_genius.py::test_get_song_details_returns_metadata -v`
Expected: FAIL (`get_song_details` not defined).

- [ ] **Step 3: Add `get_song_details` to `backend/services/genius.py`**

```python
async def get_song_details(genius_id: int) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GENIUS_API_BASE}/songs/{genius_id}",
                params={"text_format": "plain"},
                headers={"Authorization": f"Bearer {settings.genius_access_token}"},
            )
            response.raise_for_status()
            song = response.json()["response"]["song"]
    except (httpx.HTTPStatusError, httpx.RequestError):
        return {}

    album = song.get("album") or {}
    release_date = album.get("release_date_for_display", "") or song.get("release_date_for_display", "")
    release_year = release_date.split()[-1] if release_date else None

    producers = song.get("producer_artists", [])
    producer = producers[0]["name"] if producers else None

    return {
        "album_art_url": song.get("song_art_image_url"),
        "album_name": album.get("name"),
        "release_year": release_year,
        "producer": producer,
    }
```

- [ ] **Step 4: Run genius tests to confirm pass**
```bash
pytest tests/test_genius.py -v
```
Expected: all PASS.

### 5C — Backend: store and serve metadata

- [ ] **Step 5: Update `store_song` in `backend/services/supabase.py`**

Find `store_song` and add `metadata` parameter:
```python
def store_song(title: str, artist: str, lyrics: str, genius_id: Optional[int] = None, metadata: Optional[dict] = None) -> dict:
    client = get_client()
    data = {"title": title, "artist": artist, "lyrics": lyrics}
    if genius_id is not None:
        data["genius_id"] = genius_id
    if metadata:
        data["metadata"] = metadata
    result = client.table("songs").insert(data).execute()
    return result.data[0]
```

- [ ] **Step 6: Update `_format_cached` in `backend/routes/songs.py`**

Add `metadata` to the returned dict:
```python
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
        "metadata": song.get("metadata"),
    }
```

- [ ] **Step 7: Wire metadata fetch into `POST /analyze` in `backend/routes/songs.py`**

In the `analyze` route, after `genius_data = await genius_service.search_song(...)`, add:
```python
    genius_data = await genius_service.search_song(request.title, request.artist)
    song_metadata = await genius_service.get_song_details(genius_data["genius_id"])
    lyrics = await genius_service.fetch_lyrics(genius_data["url"])
    ...
    song = supabase_service.store_song(
        request.title, request.artist, lyrics, genius_data.get("genius_id"), metadata=song_metadata
    )
```

Also update the return dict for the new song case to include metadata:
```python
    return {
        "id": song["id"],
        "title": song["title"],
        "artist": song["artist"],
        "lyrics": song["lyrics"],
        "genius_id": song.get("genius_id"),
        "created_at": song.get("created_at"),
        "interpretation": interpretation,
        "community_commentary": excerpts,
        "metadata": song_metadata,
    }
```

- [ ] **Step 8: Update `backend/models/schemas.py`**

Add `SongMetadata` model and update `SongResponse`:
```python
class SongMetadata(BaseModel):
    album_art_url: Optional[str] = None
    album_name: Optional[str] = None
    release_year: Optional[str] = None
    producer: Optional[str] = None


class SongResponse(BaseModel):
    id: str
    title: str
    artist: str
    lyrics: str
    genius_id: Optional[int] = None
    created_at: Optional[datetime] = None
    interpretation: Optional[InterpretationContent] = None
    community_commentary: Optional[list[DiscourseExcerpt]] = None
    metadata: Optional[SongMetadata] = None
```

- [ ] **Step 9: Run all backend tests**
```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/backend
pytest tests/ -q
```
Expected: all PASS.

### 5D — Frontend: SongBanner component

- [ ] **Step 10: Update `frontend/types/song.ts`**

Add `SongMetadata` and update `Song`:
```typescript
export interface SongMetadata {
  album_art_url: string | null;
  album_name: string | null;
  release_year: string | null;
  producer: string | null;
}

export interface Song {
  id: string;
  title: string;
  artist: string;
  lyrics: string;
  genius_id: number | null;
  created_at: string;
  interpretation: Interpretation | null;
  community_commentary: DiscourseExcerpt[] | null;
  metadata?: SongMetadata | null;
}
```

- [ ] **Step 11: Create `frontend/components/SongBanner.tsx`**

The banner uses the album art as a blurred full-bleed background (CSS-only, no color extraction library needed). The art is blurred, darkened, and the metadata sits on top:

```tsx
import { Song } from '@/types/song';

export default function SongBanner({ song }: { song: Song }) {
  const meta = song.metadata;
  const albumArt = meta?.album_art_url ?? null;

  return (
    <div className="relative overflow-hidden rounded-xl mb-8 min-h-48">
      {/* Blurred album art background */}
      {albumArt && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={albumArt}
          alt=""
          aria-hidden
          className="absolute inset-0 w-full h-full object-cover scale-110 blur-2xl opacity-50"
        />
      )}
      {/* Dark gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/50 to-neutral-950" />

      {/* Content */}
      <div className="relative z-10 flex gap-6 p-6 items-end">
        {albumArt && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={albumArt}
            alt={`${song.title} album art`}
            width={120}
            height={120}
            className="rounded-lg shadow-2xl shrink-0 hidden sm:block"
          />
        )}
        <div className="min-w-0">
          <h1 className="text-3xl font-black text-white leading-tight">{song.title}</h1>
          <p className="text-neutral-300 text-lg mt-1">{song.artist}</p>
          <div className="flex flex-wrap gap-x-6 gap-y-1 mt-3 text-xs text-neutral-400">
            {meta?.album_name && (
              <span><span className="text-neutral-500">Album</span> {meta.album_name}</span>
            )}
            {meta?.release_year && (
              <span><span className="text-neutral-500">Year</span> {meta.release_year}</span>
            )}
            {meta?.producer && (
              <span><span className="text-neutral-500">Produced by</span> {meta.producer}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 12: Update `frontend/app/song/[id]/page.tsx`**

Add import:
```tsx
import SongBanner from '@/components/SongBanner';
```

Replace the existing song title/artist block:
```tsx
// Remove this:
<div className="mb-8">
  <h1 className="text-3xl font-black text-white">{song.title}</h1>
  <p className="text-neutral-400 text-lg">{song.artist}</p>
</div>

// Replace with:
<SongBanner song={song} />
```

- [ ] **Step 13: TypeScript check**
```bash
cd /Users/thomzillaster/Desktop/gitrepos/ai-music-analyzer/frontend
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 14: Commit**
```bash
git add backend/migrations/006_song_metadata.sql \
  backend/services/genius.py backend/services/supabase.py \
  backend/routes/songs.py backend/models/schemas.py \
  backend/tests/test_genius.py backend/tests/test_routes.py \
  frontend/types/song.ts frontend/components/SongBanner.tsx \
  "frontend/app/song/[id]/page.tsx"
git commit -m "feat: song banner with album art, blurred color background, album/year/producer metadata"
```

---

## Final: push

```bash
git push
```

---

## Notes

- **Migration 006** must be run in Supabase SQL Editor before Task 5 backend tests will pass against a real DB. Unit tests use mocks so they pass without it.
- **Billboard.py** scrapes Billboard.com — if the chart is unavailable (network, scraping block), `get_hot_100` returns an empty list and the home page shows the empty state message gracefully.
- **Existing songs** (in DB before Task 5) will have `metadata: null`. `SongBanner` handles this gracefully — the banner still renders with title and artist, no album art, no background image.
- **Existing songs** (in DB before Task 3) will have no `tldr` in their stored interpretation JSON. `AnalysisPanel` handles `interpretation.tldr` being `undefined` — it falls back to showing `overall_meaning` directly.
- **Color extraction:** The banner uses CSS blur + dark overlay instead of a color extraction library. This avoids CORS issues with Genius image URLs and requires no extra dependencies. The visual effect (album art bleeding through a dark veil) is the same pattern used by Apple Music and Spotify.
