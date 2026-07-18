# Similar Songs ("If you liked this") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On each song page, show up to 3 already-analyzed songs from the corpus that share themes/emotional tone with the current song.

**Architecture:** Pure Postgres/Python scoring against the existing `interpretations` JSONB — no new Claude spend. New backend endpoint `GET /song/{id}/similar` returns a ranked list; a client component fetches and renders it as a small row on the song page.

**Tech Stack:** FastAPI, supabase-py (PostgREST), Next.js App Router, existing `Song` types.

---

## File Structure

- **Modify:** `backend/services/supabase.py` — add `find_similar_songs(song_id, limit)` scoring helper.
- **Modify:** `backend/routes/songs.py` — add `GET /song/{id}/similar` route.
- **Modify:** `backend/models/schemas.py` — add `SimilarSong` response model.
- **Modify:** `backend/tests/test_routes.py` — coverage for the new route.
- **Modify:** `backend/tests/conftest.py` — if a new supabase stub is needed for hermetic tests.
- **Create:** `frontend/components/SimilarSongs.tsx` — client component that fetches + renders.
- **Modify:** `frontend/lib/api.ts` — add `getSimilarSongs(id)`.
- **Modify:** `frontend/types/song.ts` — add `SimilarSong` interface.
- **Modify:** `frontend/app/song/[id]/page.tsx` — mount `<SimilarSongs songId={song.id} />` under existing content.

---

### Task 1: Backend — `find_similar_songs` scoring helper

**Files:**
- Modify: `backend/services/supabase.py`

The scoring rule (documented in the docstring):
- `+3` per theme shared with the reference song
- `+1` if `emotional_tone` matches (case-insensitive)
- `+2` if same `artist` (case-insensitive)
- Require score ≥ 3 (i.e. at least one shared theme) so results feel intentional even with a small corpus.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_supabase.py` (create the file if it doesn't exist):

```python
from unittest.mock import patch, MagicMock
import services.supabase as sb


def _row(song_id, title, artist, themes, tone, tldr=None, art=None):
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
    reference = _row("s1", "A", "Artist X", ["grief", "memory"], "melancholy")
    other_high = _row("s2", "B", "Artist X", ["grief", "memory"], "melancholy")  # 3+3+1+2=9
    other_mid = _row("s3", "C", "Artist Y", ["grief"], "hopeful")               # 3
    other_low = _row("s4", "D", "Artist Z", ["joy"], "hopeful")                 # 0 (dropped)

    client = MagicMock()
    # Reference lookup returns just the reference row.
    ref_result = MagicMock()
    ref_result.data = [reference]
    # Candidate scan returns all rows except the reference.
    cand_result = MagicMock()
    cand_result.data = [other_high, other_mid, other_low]

    ref_chain = MagicMock()
    ref_chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = ref_result
    cand_chain = MagicMock()
    cand_chain.select.return_value.neq.return_value.limit.return_value.execute.return_value = cand_result

    client.table.side_effect = [ref_chain, cand_chain]

    with patch("services.supabase.get_client", return_value=client):
        results = sb.find_similar_songs("s1", limit=3)

    assert [r["id"] for r in results] == ["s2", "s3"]  # low dropped, high first
    assert results[0]["shared_themes"] == ["grief", "memory"]
    assert results[1]["shared_themes"] == ["grief"]


def test_find_similar_songs_returns_empty_when_reference_missing():
    client = MagicMock()
    ref_result = MagicMock()
    ref_result.data = []
    ref_chain = MagicMock()
    ref_chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = ref_result
    client.table.return_value = ref_chain

    with patch("services.supabase.get_client", return_value=client):
        assert sb.find_similar_songs("does-not-exist") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_supabase.py -v`
Expected: FAIL — `AttributeError: module 'services.supabase' has no attribute 'find_similar_songs'`

- [ ] **Step 3: Implement `find_similar_songs`**

Add to `backend/services/supabase.py` (near `find_songs_by_theme`):

```python
def find_similar_songs(song_id: str, limit: int = 3) -> list[dict]:
    """Return up to `limit` analyzed songs most similar to `song_id`.

    Scoring: +3 per shared theme, +1 same emotional_tone (ci), +2 same artist (ci).
    Requires score >= 3 (at least one shared theme) so low-signal results are dropped.
    Returned shape: [{id, title, artist, thumbnail, tldr, shared_themes, score}].
    """
    client = get_client()

    ref_result = (
        client.table("interpretations")
        .select("content, songs(id, title, artist)")
        .eq("song_id", song_id)
        .limit(1)
        .execute()
    )
    if not (ref_result.data or []):
        return []
    ref = ref_result.data[0]
    ref_content = ref.get("content") or {}
    ref_song = ref.get("songs") or {}
    ref_themes = {t.strip().lower() for t in (ref_content.get("themes") or []) if isinstance(t, str)}
    if not ref_themes:
        return []
    ref_tone = (ref_content.get("emotional_tone") or "").strip().lower()
    ref_artist = (ref_song.get("artist") or "").strip().lower()

    cand_result = (
        client.table("interpretations")
        .select("content, songs(id, title, artist, metadata)")
        .neq("song_id", song_id)
        .limit(10000)
        .execute()
    )

    scored: list[tuple[int, dict]] = []
    seen: set[str] = set()
    for row in cand_result.data or []:
        song = row.get("songs") or {}
        sid = song.get("id")
        if not sid or sid in seen:
            continue
        seen.add(sid)
        content = row.get("content") or {}
        themes = [t for t in (content.get("themes") or []) if isinstance(t, str)]
        shared = [t for t in themes if t.strip().lower() in ref_themes]
        if not shared:
            continue
        score = 3 * len(shared)
        if (content.get("emotional_tone") or "").strip().lower() == ref_tone and ref_tone:
            score += 1
        if (song.get("artist") or "").strip().lower() == ref_artist and ref_artist:
            score += 2
        scored.append((score, {
            "id": sid,
            "title": song.get("title", ""),
            "artist": song.get("artist", ""),
            "thumbnail": (song.get("metadata") or {}).get("album_art_url"),
            "tldr": content.get("tldr"),
            "shared_themes": shared,
            "score": score,
        }))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [entry for _, entry in scored[:limit]]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_supabase.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/supabase.py backend/tests/test_supabase.py
git commit -m "feat(similar-songs): add find_similar_songs scoring helper"
```

---

### Task 2: Backend — `GET /song/{id}/similar` route

**Files:**
- Modify: `backend/models/schemas.py`
- Modify: `backend/routes/songs.py`
- Modify: `backend/tests/test_routes.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_routes.py`:

```python
def test_get_similar_songs_returns_ranked_list():
    similar = [
        {"id": "s2", "title": "B", "artist": "X", "thumbnail": "a.jpg",
         "tldr": "…", "shared_themes": ["grief"], "score": 5},
    ]
    with patch("routes.songs.supabase_service.find_similar_songs", return_value=similar):
        response = client.get("/song/s1/similar")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == "s2"
    assert body[0]["shared_themes"] == ["grief"]


def test_get_similar_songs_returns_empty_when_none_match():
    with patch("routes.songs.supabase_service.find_similar_songs", return_value=[]):
        response = client.get("/song/s1/similar")
    assert response.status_code == 200
    assert response.json() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_routes.py -k similar -v`
Expected: FAIL — 404 (route doesn't exist).

- [ ] **Step 3: Add the response model**

In `backend/models/schemas.py`, after `ThemeSongResult`:

```python
class SimilarSong(BaseModel):
    id: str
    title: str
    artist: str
    thumbnail: Optional[str] = None
    tldr: Optional[str] = None
    shared_themes: list[str] = []
    score: int
```

- [ ] **Step 4: Add the route**

In `backend/routes/songs.py`, import the new model at the top:

```python
from models.schemas import AnalyzeRequest, AlbumResponse, ArtistResponse, SimilarSong
```

Add the route near the other `/song/{song_id}` handler:

```python
@router.get("/song/{song_id}/similar", response_model=list[SimilarSong])
async def get_similar(song_id: str, limit: int = Query(default=3, ge=1, le=10)):
    """Return songs sharing themes/tone with `song_id`, scored and ranked."""
    return supabase_service.find_similar_songs(song_id, limit=limit)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_routes.py -k similar -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/models/schemas.py backend/routes/songs.py backend/tests/test_routes.py
git commit -m "feat(similar-songs): add GET /song/{id}/similar route"
```

---

### Task 3: Frontend — `SimilarSong` type + API helper

**Files:**
- Modify: `frontend/types/song.ts`
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Add the type**

In `frontend/types/song.ts`, after `ThemeSongResult`:

```typescript
export interface SimilarSong {
  id: string;
  title: string;
  artist: string;
  thumbnail: string | null;
  tldr: string | null;
  shared_themes: string[];
  score: number;
}
```

- [ ] **Step 2: Add the API helper**

In `frontend/lib/api.ts`:

```typescript
import { Song, SearchResults, BillboardSong, Article, TrendingTheme, Album, Artist, ThemeSongResult, DeezerAlbum, SimilarSong } from '@/types/song';
```

Add at the bottom:

```typescript
export async function getSimilarSongs(id: string, limit = 3): Promise<SimilarSong[]> {
  const res = await fetch(`${BASE_URL}/song/${id}/similar?limit=${limit}`, { cache: 'no-store' });
  if (!res.ok) return [];
  return res.json();
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/types/song.ts frontend/lib/api.ts
git commit -m "feat(similar-songs): add frontend type and API helper"
```

---

### Task 4: Frontend — `SimilarSongs` component

**Files:**
- Create: `frontend/components/SimilarSongs.tsx`

- [ ] **Step 1: Create the component**

```tsx
'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { SimilarSong } from '@/types/song';
import { getSimilarSongs } from '@/lib/api';

export default function SimilarSongs({ songId }: { songId: string }) {
  const [items, setItems] = useState<SimilarSong[] | null>(null);

  useEffect(() => {
    let alive = true;
    getSimilarSongs(songId, 3).then(list => {
      if (alive) setItems(list);
    });
    return () => { alive = false; };
  }, [songId]);

  if (!items || items.length === 0) return null;

  return (
    <section className="mt-10">
      <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">
        If you liked this
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {items.map(s => (
          <Link
            key={s.id}
            href={`/song/${s.id}`}
            className="flex items-center gap-3 bg-neutral-900 hover:bg-neutral-800 rounded-lg p-3 transition-colors"
          >
            {s.thumbnail ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={s.thumbnail}
                alt=""
                width={48}
                height={48}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
                className="w-12 h-12 rounded object-cover shrink-0"
              />
            ) : (
              <div className="w-12 h-12 rounded bg-neutral-700 shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-semibold truncate">{s.title}</p>
              <p className="text-neutral-400 text-xs truncate">{s.artist}</p>
              <p className="text-purple-400 text-[10px] uppercase tracking-widest mt-0.5 truncate">
                shares: {s.shared_themes.slice(0, 2).join(', ')}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/SimilarSongs.tsx
git commit -m "feat(similar-songs): SimilarSongs client component"
```

---

### Task 5: Wire into the song page

**Files:**
- Modify: `frontend/app/song/[id]/page.tsx`

- [ ] **Step 1: Import and mount**

Add import at the top:

```tsx
import SimilarSongs from '@/components/SimilarSongs';
```

In the return, inside the analysis column `<div className="flex-1 min-w-0 w-full">`, add `<SimilarSongs songId={song.id} />` immediately after `<AnalysisPanel …/>`:

```tsx
<div className="flex-1 min-w-0 w-full">
  <AnalysisPanel
    interpretation={song.interpretation}
    commentary={song.community_commentary}
    onRequestDeepAnalysis={handleRequestDeep}
    deepAnalysisLoading={deepLoading}
    deepAnalysisError={deepError}
  />
  <SimilarSongs songId={song.id} />
</div>
```

- [ ] **Step 2: Manual verify in the browser**

Run: `cd frontend && npm run dev`
Load a song with an existing interpretation and at least a few analyzed peers in the corpus. The "If you liked this" row should appear under the analysis. If the corpus is thin, the row hides itself.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/song/[id]/page.tsx
git commit -m "feat(similar-songs): mount SimilarSongs on the song page"
```
