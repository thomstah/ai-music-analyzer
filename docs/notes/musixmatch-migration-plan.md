# Musixmatch Migration Plan

**Status:** Reference doc. Captured 2026-06-29 when Musixmatch confirmed they no longer offer a free tier.

This doc covers the architectural changes required when migrating from Genius lyrics scraping (current dev state) to a licensed Musixmatch integration. The constraints from Musixmatch's Basic plan dramatically change how the product needs to work.

---

## Musixmatch Basic plan: the actual numbers

**Price:** $49/month (~$588/year)

**Rate limits:**
| Endpoint type | Calls per day |
|---|---|
| Total API calls | 5,000 |
| **Lyrics calls** | **500** |
| Translations | 500 |
| Lyrics analysis | 100 |
| Lyrics fingerprint | 50 |

**Included:**
- Music metadata
- Static (full) lyrics text

**NOT included:**
- Time-synced lyrics
- **Lyrics caching** ← critical constraint

---

## The two constraints that drive the architectural shift

### 1. No lyrics caching allowed

You **cannot store lyrics in your database**. Musixmatch licenses per-display: every time a user views lyrics, you must make a fresh API call. The current `songs.lyrics` column pattern (fetch once, cache forever, serve from DB) is a license violation.

### 2. 500 lyrics calls per day cap

That's ~21 calls/hour averaged. Practical realism:

| Scenario | Lyrics calls/day | Fits 500? |
|---|---|---|
| 100 unique songs analyzed (Claude needs lyrics) | 100 | ✅ Plenty |
| Above + 50 users each viewing 5 songs' lyrics | 100 + 250 = 350 | ✅ Fits |
| 200 users × 5 song views | 1,000 | ❌ Over 2× |

Showing full lyrics on every page view is not feasible at any meaningful traffic. The product UX must shift to analysis-first with lyrics as opt-in.

---

## What you CAN cache

The licensing restriction targets only the **lyrics text**. Everything else stays cacheable:

| Data | Cacheable? | Source |
|---|---|---|
| Full lyrics text | ❌ No | Musixmatch (live every time) |
| Lyric *excerpts* (short quotes inside breakdowns) | ✅ Yes | Captured during analysis |
| Song metadata (title, artist, album) | ✅ Yes | Musixmatch metadata or Genius |
| Claude's AI analysis (overall_meaning, themes, etc.) | ✅ Yes | Your derivative work |
| Community annotations (Genius referents) | ✅ Yes | Genius API |
| Album art, artist photo | ✅ Yes | Deezer / Genius |
| Producer credits, album metadata | ✅ Yes | Genius API |

**The key insight:** Claude's analysis can quote 1-2 lines of lyric per breakdown ("when the artist sings 'X,' they mean Y…"), and those short quotes ARE storable. They're your derivative commentary, well within fair-use bounds. So you preserve the value of line-by-line breakdowns without storing full lyrics.

---

## Recommended product framing post-migration

Pivot from "lyrics + analysis" to **"AI music criticism with key-lyric excerpts"** — closer to a music magazine than a lyrics site.

### Default song page view (most users, most visits — **0 lyrics calls**)
- Song banner (cached metadata)
- TL;DR + full meaning (cached Claude analysis)
- Themes, emotional tone (cached)
- Line breakdowns showing only the quoted lyric + Claude's commentary (cached, no full lyrics)
- Community annotations from Genius (cached)
- Clear "View full lyrics on Musixmatch ↗" link

### Optional "Show full lyrics" toggle (user wants it — **1 lyrics call**)
- Click button → fetch from Musixmatch → display in-session only → never persist
- After page refresh, lyrics are gone until re-fetched

### Deep analysis flow (new song analyzed — **1 lyrics call**)
- Fetch lyrics from Musixmatch
- Pass to Claude with instructions to quote 5-10 key lines verbatim in breakdowns
- Persist Claude's analysis (with quoted snippets baked in)
- Discard the full lyrics text

### Realistic daily budget at this architecture
- 100 new songs analyzed/day = 100 calls
- 50 users clicking "Show full lyrics" = 50 calls
- **Total: 150/day**, leaves 350-call headroom inside the 500/day cap

This pattern scales until you have real traffic and can justify a higher-tier Musixmatch plan.

---

## Concrete code changes when migrating

| File | Change |
|---|---|
| `backend/services/musixmatch.py` | Already wired up — no change |
| `backend/routes/songs.py` `/analyze` | Stop fetching lyrics at search time. Just store song metadata. No `lyrics` field populated. |
| `backend/routes/songs.py` `/songs/{id}/deep-analyze` | Fetch lyrics from Musixmatch → pass to Claude → discard. |
| `backend/routes/songs.py` `GET /songs/{id}/lyrics` (NEW) | Live Musixmatch fetch, no DB write, returns lyrics for in-memory display only. Rate-limited per user. |
| `backend/services/anthropic.py` | Update system prompt to require Claude to quote specific lyric lines verbatim in `key_lyric_breakdowns` (so breakdowns survive without separate full-lyrics access). |
| `backend/services/supabase.py` | Drop or stop populating `songs.lyrics` column. (Could keep column unused to avoid migration.) |
| `frontend/components/LyricsPanel.tsx` | Add "Show full lyrics" toggle. Default hidden. Click → fetch from new `/songs/{id}/lyrics` endpoint → show in-memory only. |
| `frontend/app/song/[id]/page.tsx` | Default view becomes analysis-first. Lyrics behind toggle. "View on Musixmatch" link always present. |

Estimated work: ~half-day when ready to swap.

---

## Cost / break-even math

| Cost | Amount/mo |
|---|---|
| Musixmatch Basic | $49 |
| Claude (estimated for ~500 analyses/mo at avg $0.03) | $15 |
| Hosting (Supabase free tier, Railway backend ~$5) | $5 |
| Domain | $1 (amortized) |
| **Total fixed monthly** | **~$70** |

At $4.99/mo subscription: **14 paying subscribers needed to break even**.

At $7.99/mo: **9 paying subscribers**.

Realistic for a small launch but means you need at least a few hundred free users (at ~2-5% conversion) before the math works.

---

## Alternatives if $49/mo Basic feels too steep

1. **Stay on Genius scraping for dev/beta indefinitely** — what you're doing now. The legal risk is real but enforcement against small free hobby projects is rare. Migration becomes the day-before-launch task.

2. **Apply for Musixmatch commercial/enterprise tier directly** — for higher-volume apps, per-call pricing can be cheaper than Basic. Worth contacting sales before paying $49/mo.

3. **Skip lyrics display entirely** — true "music criticism only" model:
   - Source lyrics privately for Claude analysis (could use LRCLIB free community DB, or scrape only at analysis time and never store/display)
   - Display ONLY the analysis + key-lyric excerpts to users
   - Always link out to Genius/Spotify for full lyrics
   - Strongest legal posture, no licensing fees, smaller product

4. **LRCLIB** — community lyrics DB, free, no auth, no per-display restrictions. Less reliable catalog (many gaps) and unclear long-term legality but commonly used by FOSS music players. Could supplement Musixmatch as a fallback.

---

## Trigger conditions for the migration

Do the migration the day BEFORE any of these happen:
- Public LinkedIn / social media post about the product
- First paying customer signup
- First press / blog mention
- First time you tell anyone non-trivially about it (recruiter, investor, etc.)

Until then: stay on Genius scraping is acceptable risk for a hobby/dev project.

---

## Related files

- [Business model brainstorm](./business-model-brainstorm.md) — Pricing tiers, auth, payments
- [Legal templates](./legal-templates.md) — Terms / Privacy / DMCA scaffolds
- `backend/services/musixmatch.py` — Already wired, not wired into the analyze flow
- `backend/services/genius.py` — `fetch_lyrics()` is the function to remove when migrating
