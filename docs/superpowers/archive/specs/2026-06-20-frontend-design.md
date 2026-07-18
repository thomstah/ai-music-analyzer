# Frontend Design Spec

**Date:** 2026-06-20
**Scope:** MVP frontend + small backend additions to support it
**Status:** Working draft — subject to iteration before public release

---

## Goal

Build a Genius-style dark-mode web UI on top of the existing FastAPI backend. Users can browse trending songs, search by title and artist, and read lyrics alongside Claude's AI interpretation. Clicking a lyric line surfaces Claude's pre-analyzed breakdown for that line.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS |
| HTTP client | Native `fetch` (server components) + `fetch` in client components |

Lives at `/frontend` in the monorepo alongside `/backend`.

---

## Pages

### `/` — Home

- **Navbar:** Logo (left), two-field search form (Song Title + Artist Name inputs), submit button
- **Trending chart:** Fetches `GET /songs/trending?limit=10` on load. Renders an ordered list of songs with title, artist, and request count. Each row is a link to `/song/[id]`
- **Empty state:** If no songs have been analyzed yet, shows a prompt to search for the first one

### `/song/[id]` — Song Page

Two-column layout on desktop, single column on mobile.

**Left column (60%) — Lyrics:**
- Song title and artist at the top
- Lyrics rendered line by line. Each line is a clickable element
- Clicking a line highlights it purple and triggers the analysis panel to update
- Lines that have a matching `key_lyric_breakdown` get a subtle underline indicator so users know something is there

**Right column (40%) — Analysis panel (sticky):**
- Always visible: `emotional_tone` as a tag, `themes` as chips, `overall_meaning` as a collapsible paragraph
- Below the summary: breakdown slot — empty until a line is clicked
- When a line with a matching breakdown is clicked: animates in the `lyric` + `breakdown` from `key_lyric_breakdowns`
- When a line with no breakdown is clicked: panel stays on summary, no error shown
- `community_commentary` section below the breakdown — shows Genius annotations and YouTube comments as expandable quote cards

**Mobile layout:**
- Analysis panel collapses to a compact summary block at the top of the page
- Lyrics render below in full width
- Clicking a line opens a bottom sheet with the breakdown

---

## Search Flow

1. User enters song title + artist in the navbar search form
2. Frontend calls `POST /analyze` with `{title, artist}`
3. On success: navigate to `/song/[id]` using the `id` from the response. Pass full response data via URL state or cache in `sessionStorage` to avoid a second fetch
4. On 404 (song not found on Genius): show inline error in the search form
5. On slow response (AI call in progress): show loading state on the search button

---

## Backend Changes

### Migration `004_request_count.sql`

```sql
alter table songs add column request_count integer not null default 0;
```

### `services/supabase.py` changes

- `store_song`: no change needed — new rows start at `request_count = 0`
- `find_song`: after returning a cached hit, issue an update to increment `request_count`
- New function `get_trending(limit: int) -> list[dict]`: queries songs ordered by `request_count desc`, returns top N

### `routes/songs.py` changes

- New endpoint: `GET /songs/trending?limit=10` — calls `supabase_service.get_trending(limit)`, returns list of `{id, title, artist, request_count}`
- `POST /analyze`: no route change, but `find_song` now increments the count internally

---

## Component Map

```
frontend/
├── app/
│   ├── page.tsx                  # Home page
│   ├── song/[id]/page.tsx        # Song page
│   └── layout.tsx                # Root layout (Navbar, dark bg)
├── components/
│   ├── Navbar.tsx                # Logo + search form
│   ├── TrendingChart.tsx         # Ordered list of trending songs
│   ├── LyricsPanel.tsx           # Line-by-line lyrics, click to select
│   ├── AnalysisPanel.tsx         # Summary + breakdown slot + community commentary
│   └── BreakdownCard.tsx         # Single key_lyric_breakdown display
├── lib/
│   └── api.ts                    # Typed fetch wrappers for backend endpoints
└── types/
    └── song.ts                   # TypeScript types matching backend response shape
```

---

## Data Types (frontend mirrors backend response)

```typescript
interface LyricBreakdown {
  lyric: string;
  breakdown: string;
}

interface DiscourseExcerpt {
  source: "genius" | "youtube";
  text: string;
  url: string | null;
  metadata: Record<string, string>;
}

interface SongResponse {
  id: string;
  title: string;
  artist: string;
  lyrics: string;
  genius_id: number | null;
  created_at: string;
  interpretation: {
    overall_meaning: string;
    emotional_tone: string;
    themes: string[];
    key_lyric_breakdowns: LyricBreakdown[];
  } | null;
  community_commentary: DiscourseExcerpt[] | null;
}
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Song not found on Genius (404) | Inline error under search form: "Couldn't find that song on Genius" |
| `/analyze` slow (AI call) | Button shows spinner, disabled. No timeout on client — backend handles it |
| `/songs/trending` fails | Home page shows search only, no chart, no error banner |
| Song has no interpretation | Song page renders lyrics, analysis panel shows "No interpretation available" |
| Lyric line has no breakdown | Click does nothing visible — summary stays in panel |

---

## Out of Scope (This Iteration)

- User accounts / authentication
- Saving or bookmarking songs
- Sharing individual lyric breakdowns
- Real-time AI highlight analysis (on-demand Claude calls per highlight)
- Dynamic chart TTL based on request frequency
- Dark/light mode toggle
