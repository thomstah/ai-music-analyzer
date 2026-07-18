# Discourse Integration Design

## Goal

Enrich Claude's song interpretations with real community commentary by scraping Reddit threads and Genius annotations, then surfacing both as Claude context and raw excerpts in the API response.

## Architecture

Five changes to the existing codebase:

| Change | What |
|---|---|
| New `services/discourse.py` | Fetches Reddit threads + Genius annotations, returns unified excerpt list |
| New `discourse` Supabase table | Stores excerpts per song with `scraped_at` for TTL |
| Updated `services/supabase.py` | Adds `find_discourse`, `store_discourse` |
| Updated `services/anthropic.py` | `generate_interpretation` accepts optional discourse excerpts, weaves them into the user message |
| Updated `routes/songs.py` + `models/schemas.py` | Calls discourse service, passes to Claude, returns `community_commentary` field |

**Data flow for `/analyze`:**
1. Check Supabase for song
2. Check Supabase for discourse (TTL check) — independent of song cache
3. If song found AND discourse is fresh (< 7 days): return cached song + cached discourse
4. If song found BUT discourse is stale/missing: re-scrape discourse, update Supabase, return cached song + fresh discourse
5. If song not found: fetch lyrics from Genius, scrape discourse fresh, pass both to Claude, store song + interpretation + discourse, return full response

**Future improvement:** Dynamic TTL based on request frequency — popular songs get fresher discourse (e.g. 1-day TTL at 100+ requests/day vs 7-day TTL at low traffic). Not built in this iteration; fixed 7-day TTL used instead.

## Data Models

**New Supabase table:**
```sql
create table discourse (
  id uuid primary key default gen_random_uuid(),
  song_id uuid not null references songs(id) on delete cascade,
  excerpts jsonb not null,
  scraped_at timestamptz default now()
);
```

**New Pydantic schema (`models/schemas.py`):**
```python
class DiscourseExcerpt(BaseModel):
    source: str                # "reddit" or "genius"
    text: str                  # comment or annotation body
    url: Optional[str]         # Reddit thread URL; None for Genius annotations
    metadata: dict             # {"subreddit": "r/hiphopheads"} or {"lyric_fragment": "..."}
```

**Updated `SongResponse`:**
```python
community_commentary: Optional[list[DiscourseExcerpt]] = None
```

## Discourse Scraping

### Reddit
- Uses the unofficial Reddit JSON API — no API key required
- Search: `GET https://www.reddit.com/search.json?q="{title}"+"{artist}"&sort=top&t=all&limit=5`
- For each thread, fetch top comments: `GET https://www.reddit.com/r/{subreddit}/comments/{id}.json?sort=top&limit=5`
- Top 3 comments per thread, capped at 10 Reddit excerpts total
- Requires `User-Agent: ai-music-analyzer/1.0` header to avoid 429s
- Filter out comments under 50 characters

### Genius Annotations
- Uses existing `GENIUS_ACCESS_TOKEN`
- `GET https://api.genius.com/referents?song_id={genius_id}&text_format=plain`
- Returns all fan-annotated lyric fragments with annotation bodies
- Take top 5 by annotation text length (longer = more substantive)
- Skipped entirely if `genius_id` is `None`

## Claude Prompt Changes

The system prompt is unchanged. When discourse is available, the user message is extended:

```
Song: "{title}" by {artist}

Lyrics:
{lyrics}

Community Commentary (Reddit threads and Genius annotations — use these to inform your interpretation):
[reddit] r/hiphopheads: "This song is about Drake processing..."
[genius] "I sipped lean and lost my mind" → "Reference to the Houston lean culture..."
...

Return the same JSON structure as before.
```

Claude returns the same 4-field JSON (`overall_meaning`, `emotional_tone`, `themes`, `key_lyric_breakdowns`). Discourse is not echoed back — it is returned separately as `community_commentary`.

## Error Handling

| Scenario | Behavior |
|---|---|
| Reddit 429 / rate limited | Log warning, skip Reddit excerpts, continue with Genius only |
| Reddit returns no results | `community_commentary` includes Genius annotations only |
| Genius referents API fails | Log warning, skip Genius annotations, continue with Reddit only |
| Both sources fail | `community_commentary` is `[]`; Claude interprets from lyrics alone |
| `genius_id` is `None` | Skip Genius annotations entirely |
| Discourse cache hit (< 7 days) | Skip all scraping, use stored excerpts |

No request ever hard-fails due to discourse scraping. The analyze flow always completes — discourse is additive.

## Testing

Each new/modified unit gets its own test file or extended test suite:

- `tests/test_discourse.py` — mock httpx calls for both Reddit and Genius referents endpoints; test TTL logic, graceful degradation on failure, comment filtering
- `tests/test_supabase.py` — extend with `find_discourse` and `store_discourse` tests
- `tests/test_anthropic.py` — extend with test for discourse-enriched prompt path
- `tests/test_routes.py` — extend with end-to-end mock covering `community_commentary` in response
