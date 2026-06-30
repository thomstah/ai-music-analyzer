# Analysis-First Refactor

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure song page to be analysis-first with lyrics on-demand. Mirror Musixmatch architecture so Genius is a swappable adapter.

**Architecture:** Lyrics are ephemeral — fetched per-display via `GET /songs/{id}/lyrics`, never cached in the DB by new flows. Claude prompt updated so breakdowns include verbatim quoted lyrics (self-contained). UI is single-column long-read with slide-in lyrics drawer.

**Tech Stack:** Same as today. No new dependencies.

**Cost-cap context:** This refactor is for the [cost-capped launch plan](../../notes/cost-capped-launch-plan.md), not a paywall. The deep-analyze endpoint will check a monthly Claude budget (set by the operator), not a per-user subscription tier. No auth, no Stripe subscriptions involved.

---

## File Map

### Backend
| File | Change |
|---|---|
| `backend/services/anthropic.py` | Update SYSTEM_PROMPT to require verbatim lyric quotes in breakdowns |
| `backend/routes/songs.py` | `/analyze` stops fetching lyrics; new `GET /songs/{id}/lyrics`; `/songs/{id}/deep-analyze` fetches + discards |
| `backend/services/genius.py` | Add `fetch_lyrics_by_title_artist(title, artist)` convenience that combines `search_song` + `fetch_lyrics` |
| `backend/routes/songs.py` | Add `POST /admin/reanalyze-all` for one-off backfill |
| `backend/tests/test_routes.py` | Update analyze test, add lyrics endpoint test, add reanalyze test |

### Frontend
| File | Change |
|---|---|
| `frontend/types/song.ts` | `Song.lyrics` becomes optional |
| `frontend/lib/api.ts` | Add `getSongLyrics(id)` |
| `frontend/components/LyricsDrawer.tsx` | NEW — slide-in from right, fetches on open |
| `frontend/components/BreakdownCard.tsx` | Make standalone (large quoted lyric + commentary) |
| `frontend/components/AnalysisPanel.tsx` | Convert to long-read; remove sticky sidebar styling |
| `frontend/app/song/[id]/page.tsx` | Single-column layout, remove LyricsPanel, add LyricsDrawer button |
| `frontend/components/LyricsPanel.tsx` | Keep but used only inside drawer; remove click-to-explain props |

---

## Task 1: Update Claude prompt

- [ ] **Step 1: Modify `SYSTEM_PROMPT` in `backend/services/anthropic.py`**

Add explicit instruction: each `key_lyric_breakdowns` entry must include 5-10 verbatim lyric lines as the `lyric` field, separated by newlines. The `breakdown` field is the commentary on those lines.

- [ ] **Step 2: Verify schema still accepts multi-line `lyric` strings**

`LyricBreakdown.lyric: str` already accepts any string. No schema change.

- [ ] **Step 3: Run tests**

```bash
cd backend && pytest tests/ -q
```

---

## Task 2: Backend route refactor

- [ ] **Step 4: Modify `/analyze` in `backend/routes/songs.py`**

Remove the `genius_service.fetch_lyrics(...)` call. Store song with empty lyrics string. Return without lyrics.

- [ ] **Step 5: Add `GET /songs/{id}/lyrics` endpoint**

```python
@router.get("/songs/{song_id}/lyrics")
async def get_song_lyrics(song_id: str):
    song = supabase_service.get_song_by_id(song_id)
    if not song or not song.get("genius_id"):
        raise HTTPException(status_code=404, detail="Song not found")
    # Re-search Genius (cheap; cached internally) to get the URL
    genius_data = await genius_service.search_song(song["title"], song["artist"])
    lyrics = await genius_service.fetch_lyrics(genius_data["url"])
    return {"lyrics": lyrics}
```

- [ ] **Step 6: Modify `/songs/{id}/deep-analyze`**

Fetch lyrics live from Genius (don't read from `songs.lyrics`). Pass to Claude. Don't write lyrics back.

- [ ] **Step 7: Add `POST /admin/reanalyze-all`**

Iterates over all interpretation rows. For each, fetches song's lyrics from Genius, calls Claude with new prompt, updates the interpretation content. Returns `{updated: N}`.

- [ ] **Step 8: Update tests**

---

## Task 3: Frontend refactor

- [ ] **Step 9: Update types and API client**

Make `Song.lyrics` optional. Add `getSongLyrics(id: string): Promise<string | null>` in `lib/api.ts`.

- [ ] **Step 10: Create `LyricsDrawer.tsx`**

Slide-in from right. Fetches on mount/open. Shows spinner. Close on Escape, X, outside-click. Inside, renders `<LyricsPanel>` in read-only mode (no click handlers).

- [ ] **Step 11: Update `BreakdownCard.tsx`**

Each card shows the quoted lyric as a prominent block (italic, bordered, multi-line), then the commentary underneath.

- [ ] **Step 12: Refactor `AnalysisPanel.tsx`**

Drop the sticky-sidebar styling. Convert to long-read content blocks. Remove `selectedBreakdown` and click-to-explain props.

- [ ] **Step 13: Refactor `app/song/[id]/page.tsx`**

Single-column layout. Remove LyricsPanel rendering. Add "Show full lyrics" button that opens LyricsDrawer.

- [ ] **Step 14: Run frontend checks**

```bash
cd frontend && npx tsc --noEmit && npx next build
```

---

## Task 4: Run backfill

- [ ] **Step 15: Call `POST /admin/reanalyze-all` once locally**

After deploying the new prompt. Updates every stored interpretation in place. Cost is ~$0.03 per song.

---

## Commit Plan

One commit per task:
1. `feat: update Claude prompt to require verbatim lyric quotes in breakdowns`
2. `refactor: lyrics fetched on-demand; analyze stores metadata only`
3. `feat: analysis-first song page with slide-in lyrics drawer`
4. `chore: re-analyze all stored songs under new prompt`

---

## Future Musixmatch swap

When ready, the only changes needed:
- `backend/services/genius.py` `fetch_lyrics` → swap to `musixmatch.fetch_lyrics_by_name`
- Add Musixmatch attribution UI inside the drawer
- Remove Genius URL dependency in `/songs/{id}/lyrics` (Musixmatch uses title+artist lookup)

Frontend doesn't change at all.
