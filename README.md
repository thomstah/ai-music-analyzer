# Lyriq

An AI-powered music criticism and commentary platform. Search any song and get a Claude-generated breakdown of its meaning, themes, emotional tone, and key lyrics — alongside community annotations from Genius and editorial context for the artist and album.

**Status:** In active development. Currently in pre-public alpha (no auth, no payments, hobby usage only). See [Roadmap](#roadmap) for the path to public release.

---

## What it does

- **Search** any song by title, artist, or lyric snippet (Apple Music-style results: artists, songs, albums, lyric matches)
- **Browse** the Billboard Hot 100, music news, trending themes across analyzed songs, and a daily featured artist
- **Song pages** show the lyrics alongside an analysis panel with community annotations and an on-demand AI deep analysis (TL;DR, themes, emotional tone, line-by-line breakdowns)
- **Album pages** show the cover, tracklist, release year, and producer credits — every track is clickable to analyze
- **Artist pages** show a Genius-style banner with bio, alternate names, popular songs, and popular albums (Deezer-sourced discography)
- **Cross-linking** between songs ↔ albums ↔ artists throughout the app

---

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3.14, FastAPI |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Database | Supabase (Postgres + Auth-ready) |
| AI | Anthropic Claude (Sonnet 4.6) |
| Lyrics | Genius (dev only) → Musixmatch (planned for public release) |
| Music metadata | Genius API, Deezer API |
| Community / news | Genius referents, YouTube comments, NewsAPI |
| Charts | `billboard.py` scraper |
| Payments (planned) | Stripe Checkout + Customer Portal |
| Auth (planned) | Supabase Auth |

---

## Architecture

The app is split cleanly into a Python backend and a Next.js frontend:

```
ai-music-analyzer/
├── backend/                    # FastAPI server
│   ├── main.py                 # App entry, lifespan handlers (Billboard cache pre-warm)
│   ├── config.py               # Settings (API keys from .env)
│   ├── routes/songs.py         # All HTTP endpoints
│   ├── services/               # External API clients + business logic
│   │   ├── genius.py           # Genius API + lyrics scraper
│   │   ├── musixmatch.py       # Musixmatch client (wired but not active)
│   │   ├── deezer.py           # Deezer API (artist photos + discography)
│   │   ├── anthropic.py        # Claude interpretation pipeline
│   │   ├── discourse.py        # Genius annotations + YouTube comments
│   │   ├── billboard.py        # Billboard Hot 100 scraper (24h cache)
│   │   ├── news.py             # NewsAPI music feed (1h cache)
│   │   └── supabase.py         # Database CRUD
│   ├── models/schemas.py       # Pydantic request/response models
│   ├── migrations/             # SQL migrations (numbered 002 → 011)
│   └── tests/                  # pytest suite (~120 tests)
├── frontend/
│   ├── app/                    # Next.js App Router pages
│   │   ├── page.tsx            # Home (Billboard, news, themes, featured artist)
│   │   ├── song/[id]/page.tsx  # Song with lyrics + analysis panel
│   │   ├── album/[id]/page.tsx # Album with tracklist
│   │   └── artist/[id]/page.tsx# Artist with top songs + albums
│   ├── components/             # React UI primitives
│   ├── lib/api.ts              # Typed fetch wrappers
│   └── types/song.ts           # Shared TypeScript interfaces
└── docs/
    ├── superpowers/plans/      # Implementation plans
    ├── superpowers/specs/      # Design specs
    └── notes/                  # Business model, legal templates, migration plan
```

### Key design decisions
- **Analysis is generated on demand**, not at song-fetch time. `POST /analyze` returns basic info (lyrics + community context) instantly; `POST /songs/{id}/deep-analyze` runs Claude only when the user explicitly requests it. This is the natural seam for a future free/premium paywall.
- **Multi-source metadata bridging**: Genius for lyrics/community/producer credits, Deezer for artist photos and discography (Genius blocks the artist albums endpoint on our access tier), Musixmatch for licensed lyrics (planned).
- **Aggressive caching** on external API responses (24h for Billboard, 5min for trending themes, 1h for news, indefinite for song/album/artist rows in Supabase).

---

## Getting started

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Supabase project (free tier works)
- API keys for: [Genius](https://genius.com/api-clients), [Anthropic](https://console.anthropic.com), [YouTube Data API v3](https://console.cloud.google.com), [NewsAPI](https://newsapi.org) (optional)

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:
```
GENIUS_ACCESS_TOKEN=...
ANTHROPIC_API_KEY=...
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
YOUTUBE_API_KEY=...
NEWSAPI_KEY=...           # optional — news panel returns [] without it
MUSIXMATCH_API_KEY=...    # optional — wired but not used in current dev setup
```

Run all migrations in your Supabase SQL Editor in numerical order (`002` through `011`). Then start the server:

```bash
uvicorn main:app --reload
```

Backend runs at `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Run:
```bash
npm run dev
```

Frontend runs at `http://localhost:3000`.

### Tests

```bash
cd backend && pytest tests/ -q     # ~120 tests, runs in <1s
cd frontend && npx tsc --noEmit    # TypeScript check
cd frontend && npm run lint        # ESLint
cd frontend && npx next build      # Production build verification
```

---

## Features by release phase

### ✅ Phase 1: Core MVP (complete)
- [x] Song search by title and artist
- [x] Genius lyrics fetching and display
- [x] Claude-generated song interpretation (overall meaning, themes, emotional tone, key-lyric breakdowns)
- [x] Persistent storage of analyzed songs in Supabase

### ✅ Phase 2: Discovery surface (complete)
- [x] Home page with Billboard Hot 100
- [x] Trending chart based on app's own request counts
- [x] Single-query unified search bar (replaces separate title/artist fields)
- [x] Genius-style two-column song page layout (lyrics + analysis)

### ✅ Phase 3: Frontend polish (complete)
- [x] Dark mode UI
- [x] Reusable loading spinner with proper accessibility
- [x] Distinct background for analysis panel (clear scroll affordance)
- [x] TL;DR-by-default with "Full analysis" toggle
- [x] Click-to-explain individual lyric lines
- [x] Genius translation accounts filtered out of search results
- [x] Compilation/box-set releases deprioritized in search
- [x] Strip "X Contributors..." boilerplate from scraped lyrics

### ✅ Phase 4: Community + context (complete)
- [x] Community annotations from Genius referents
- [x] YouTube top comments as secondary commentary
- [x] Music news panel (NewsAPI, Pitchfork/Rolling Stone/Billboard sources)
- [x] Trending themes aggregated across all analyzed songs
- [x] Featured artist banner derived from Billboard #1

### ✅ Phase 5: Search redesign + cross-linking (complete)
- [x] Apple Music-style search: artist sidebar + song grid + albums + lyrics
- [x] Albums category in search (derived from cached songs by album metadata)
- [x] Clickable artist names everywhere → artist page

### ✅ Phase 6: Album pages (complete)
- [x] Album page with cover, title, artist, year, producer credits, tracklist
- [x] Genius-style colored banner (album art blurred as background)
- [x] Clickable tracks → song analysis
- [x] Song banner's "Album" pill links back to album page

### ✅ Phase 7: Artist pages (complete)
- [x] Artist page with Genius-style banner (header image + circular photo)
- [x] Artist bio (preview + expand for full)
- [x] Popular songs (Genius `/artists/{id}/songs?sort=popularity`)
- [x] Popular albums (Deezer discography — Genius blocks this on our tier)
- [x] Deezer used for high-res profile photo (fallback to Genius)
- [x] Artist name lookup endpoint for Billboard chart clicks

### ✅ Phase 8: Basic vs deep analysis split (complete)
- [x] `POST /analyze` no longer calls Claude — returns basic info instantly
- [x] `POST /songs/{id}/deep-analyze` runs Claude on demand
- [x] Song page shows "Get deep analysis" CTA in basic mode
- [x] Architectural seam for future paywall

### 🚧 Phase 9: Pre-public migration (planned, partially scaffolded)
- [ ] Swap Genius lyrics scraper → Musixmatch (licensed, paid Basic plan)
- [ ] Restructure song page to analysis-first (lyrics behind opt-in toggle, no DB caching of lyrics text)
- [ ] Update Claude prompt to require verbatim lyric quotes inside breakdowns
- [ ] Terms of Service + Privacy Policy pages live
- [ ] DMCA designated agent registered with US Copyright Office
- [ ] AI-generated content disclaimer visible near every analysis
- [ ] Cookie consent banner (EU compliance)

### 🔮 Phase 10: Auth + payments (planned)
- [ ] Supabase Auth integration (email + Google OAuth)
- [ ] User accounts with `subscription_tier` (free / premium / beta)
- [ ] Free tier: basic analysis only (community annotations + context)
- [ ] Premium tier ($4.99/mo): unlocks Claude deep analysis
- [ ] Stripe Checkout for subscription signup
- [ ] Stripe Customer Portal for self-service management
- [ ] Stripe webhook handler with signature verification
- [ ] Beta-period mass-grant of premium access during launch

### 🔮 Phase 11: Public release
- [ ] Trademark search on "Lyriq"
- [ ] Brand site + landing page
- [ ] Email transactional setup (welcome, billing receipts)
- [ ] Analytics and error monitoring
- [ ] Production hosting (Railway/Render backend, Vercel frontend)
- [ ] LinkedIn / social launch

### 💡 Future ideas
- 30-second song previews via Spotify or Deezer
- Time-synced lyrics (requires Musixmatch Commercial tier)
- "Related artists" widget (Musixmatch has the endpoint)
- Translation support for non-English songs
- Mobile app (React Native)
- API for third-party integrations

---

## Documentation

Internal planning and reference docs live under `docs/`:

- **[`docs/superpowers/specs/`](docs/superpowers/specs/)** — Design specs for each major feature
- **[`docs/superpowers/plans/`](docs/superpowers/plans/)** — Step-by-step implementation plans
- **[`docs/notes/business-model-brainstorm.md`](docs/notes/business-model-brainstorm.md)** — Subscription tier plan, auth/payments architecture, security concerns
- **[`docs/notes/musixmatch-migration-plan.md`](docs/notes/musixmatch-migration-plan.md)** — What changes when switching from Genius scraping to licensed Musixmatch
- **[`docs/notes/legal-templates.md`](docs/notes/legal-templates.md)** — Drafts for Terms of Service, Privacy Policy, DMCA notice (require attorney review before publishing)

---

## Legal status

**This app is currently in dev/hobby mode and is not publicly accessible.** The lyrics scraping from Genius violates their Terms of Service and is acceptable only for a private, non-distributed, single-user dev environment.

Before any public release, the following must happen (tracked in Phase 9 above):
- Switch lyrics source to licensed Musixmatch
- Publish Terms of Service, Privacy Policy, and DMCA notice
- Register a DMCA designated agent
- Add AI-generated content disclaimers

See [`docs/notes/legal-templates.md`](docs/notes/legal-templates.md) and [`docs/notes/musixmatch-migration-plan.md`](docs/notes/musixmatch-migration-plan.md) for the full plan.

---

## Contributing

This is currently a solo project. The codebase is open for inspection and learning but not yet accepting outside contributions — that will change after the public release in Phase 11.

---

## Acknowledgments

- [Anthropic Claude](https://www.anthropic.com) — AI interpretation engine
- [Genius](https://genius.com) — Song metadata, annotations, lyrics (dev only)
- [Deezer](https://www.deezer.com) — Artist photos and discography
- [Musixmatch](https://www.musixmatch.com) — Licensed lyrics (planned)
- [Supabase](https://supabase.com) — Database and auth platform
- [Next.js](https://nextjs.org) and [FastAPI](https://fastapi.tiangolo.com) — Web frameworks
