# AI Music Analyzer — Backend Design Spec

**Date:** 2026-05-17  
**Scope:** MVP backend only (frontend deferred)  
**Target deployment:** Railway  

---

## Overview

A FastAPI backend that accepts a song title + artist, fetches lyrics from Genius (via scraping), generates a structured AI interpretation using Claude, and caches everything in Supabase. Repeat queries hit the cache — no redundant API calls.

---

## Project Structure

```
backend/
├── main.py                  # FastAPI app init, CORS, router registration
├── config.py                # Settings via pydantic-settings (reads from .env)
├── routes/
│   └── songs.py             # Route handlers (thin — delegate to services)
├── services/
│   ├── genius.py            # Genius API search + BeautifulSoup lyrics scraping
│   ├── anthropic.py         # Claude prompt construction + JSON response parsing
│   └── supabase.py          # All Supabase reads/writes
├── models/
│   └── schemas.py           # Pydantic request/response models
├── requirements.txt
├── .env.example
└── railway.toml
```

---

## API Routes

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/songs/search?title=&artist=` | Check Supabase cache by title + artist |
| `POST` | `/analyze` | Full flow: cache → lyrics → interpretation |
| `GET` | `/song/{id}` | Return stored song + latest interpretation |

---

## Request/Response Flow — POST /analyze

1. Check Supabase for existing song (case-insensitive title + artist match)
2. If found → return cached song + interpretation (skip remaining steps)
3. Call Genius API → get song page URL
4. Scrape Genius page with BeautifulSoup → extract lyrics text
5. Normalize lyrics (strip `[Verse]`/`[Chorus]`/`[Bridge]` headers, trim whitespace, preserve line breaks)
6. Call Claude → parse structured JSON interpretation
7. Store song + interpretation in Supabase
8. Return result

---

## Data Models

### Supabase: `songs`

```sql
id          uuid primary key default gen_random_uuid()
title       text not null
artist      text not null
lyrics      text not null
genius_id   integer
created_at  timestamptz default now()
```

### Supabase: `interpretations`

```sql
id            uuid primary key default gen_random_uuid()
song_id       uuid references songs(id)
content       jsonb not null
model_version text not null
created_at    timestamptz default now()
```

### Claude interpretation JSON shape (stored in `content`):

```json
{
  "overall_meaning": "2-3 paragraph interpretation",
  "emotional_tone": "e.g. melancholic, defiant, bittersweet",
  "themes": ["theme1", "theme2"],
  "key_lyric_breakdowns": [
    {
      "lyric": "quoted lyric fragment",
      "breakdown": "explanation of meaning/significance"
    }
  ]
}
```

---

## Cache Lookup Strategy

Match on `LOWER(title)` + `LOWER(artist)` to treat "Taylor Swift" and "taylor swift" as the same entry.

---

## Error Handling

| Failure point | Behavior |
|---------------|----------|
| Song not found on Genius | `404` with clear message |
| Lyrics scraping fails | `502` — "Could not extract lyrics" |
| Claude returns malformed JSON | Retry once with explicit JSON instruction, then `502` |
| Supabase write fails | Return result to caller, log error (don't block response) |
| Duplicate song race condition | `ON CONFLICT DO NOTHING` on insert |

---

## Environment Variables

```
GENIUS_ACCESS_TOKEN=
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
```

Never committed. Set in Railway dashboard for production, `.env` file locally.

---

## Dependencies

```
fastapi
uvicorn
httpx
beautifulsoup4
anthropic
supabase
pydantic-settings
python-dotenv
```

---

## Deployment

- Platform: Railway
- Runtime: Python 3.11 (auto-detected from `requirements.txt`)
- No Docker required
- `railway.toml` defines build + deploy commands pointing at `uvicorn main:app --host 0.0.0.0 --port $PORT`

---

## Out of Scope (MVP)

- Frontend (Next.js — deferred)
- Reddit/discourse aggregation (Phase 8)
- pgvector / semantic search (Phase 8)
- Authentication on the API itself
- Async job queue for AI calls
