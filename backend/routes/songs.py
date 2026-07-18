import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from models.schemas import AnalyzeRequest, AlbumResponse, ArtistResponse, SimilarSong
import services.supabase as supabase_service
import services.genius as genius_service
import services.deezer as deezer_service
import services.anthropic as anthropic_service
import services.discourse as discourse_service
import services.billboard as billboard_service
import services.news as news_service
import services.claude_budget as claude_budget
import services.color as color_service
import services.rate_limit as rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()

DISCOURSE_TTL_DAYS = 7


async def _refresh_discourse_bg(
    song_id: str, genius_id: Optional[int], title: str, artist: str
) -> None:
    """Fetch fresh discourse and persist it. Runs after /analyze has responded,
    so the user isn't waiting on the Reddit + Genius annotation scrape."""
    try:
        excerpts = await discourse_service.fetch_discourse(genius_id, title, artist)
        supabase_service.store_discourse(song_id, excerpts)
    except Exception as exc:
        logger.warning("Background discourse refresh failed for %s: %s", song_id, exc)


def _client_ip(request: Request) -> str:
    """Best-effort IP: prefer X-Forwarded-For's first hop when behind a proxy."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_dep(capacity: int, refill_per_sec: float, bucket: str):
    """Build a FastAPI dependency that enforces per-IP token-bucket limits.
    Raises 429 with a Retry-After header when the caller runs out of tokens."""
    async def _dep(request: Request):
        ok = await rate_limit.check(
            f"ip:{_client_ip(request)}:{bucket}",
            capacity=capacity,
            refill_per_sec=refill_per_sec,
        )
        if not ok:
            raise HTTPException(
                status_code=429,
                detail="You're going a bit fast — retry in a minute.",
                headers={"Retry-After": "60"},
            )
    return _dep


_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)

# Per-process cache for album "extras" (description, accent color) that aren't stored
# in the DB. Keyed by genius_id. Description comes from Genius; accent_color from
# colorthief on the cover art. Both are cheap to keep in memory and expensive enough
# (extra HTTP round-trip + image decode) that we don't want to redo them per request.
_album_extras_cache: dict[int, dict] = {}
# Fields returned by get_album_details that aren't stored on the albums table.
# Stripped before we upsert so the write doesn't reject unknown columns.
_EXTRAS_KEYS = ("description",)


async def _hydrate_album_extras(album: dict) -> dict:
    """Attach `description` and `accent_color` to an album row, backfilling from
    Genius + colorthief when missing. Cached in-process by genius_id."""
    gid = album.get("genius_id")
    description = album.get("description")
    accent = album.get("accent_color")

    if gid and gid in _album_extras_cache:
        cached_extras = _album_extras_cache[gid]
        description = description or cached_extras.get("description")
        accent = accent or cached_extras.get("accent_color")
    else:
        if not description and gid:
            fetched = await genius_service.get_album_details(int(gid))
            description = (fetched or {}).get("description")
        if not accent:
            cover = album.get("cover_art_url")
            if cover:
                accent = await color_service.extract_dominant_color(cover)
        if gid:
            _album_extras_cache[gid] = {"description": description, "accent_color": accent}

    return {**album, "description": description, "accent_color": accent}


async def _resolve_album(album_id: str) -> Optional[dict]:
    # UUID format → our DB id
    if _UUID_RE.match(album_id):
        by_uuid = supabase_service.get_album_by_id(album_id)
        if by_uuid:
            return by_uuid
        # Valid UUID but no row — treat as not found rather than fall through to int parse
        return None

    # Otherwise interpret as a Genius integer id — cache lookup then live fetch
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

    # Strip fields that aren't columns on the albums table before upserting.
    to_store = {k: v for k, v in fetched.items() if k not in _EXTRAS_KEYS}
    stored = supabase_service.store_album(to_store)
    # Preserve the extras on the row we return so the request doesn't re-fetch them.
    for k in _EXTRAS_KEYS:
        if k in fetched:
            stored[k] = fetched[k]
    return stored


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


def _is_discourse_fresh(row: dict) -> bool:
    scraped_at_str = row.get("scraped_at")
    if not scraped_at_str:
        return False
    scraped_at = datetime.fromisoformat(scraped_at_str.replace("Z", "+00:00"))
    return datetime.now(timezone.utc) - scraped_at < timedelta(days=DISCOURSE_TTL_DAYS)


async def _enhance_artist_photo(artist_hit: dict) -> dict:
    """Replace Genius search thumbnail with the higher-quality cached/Deezer photo
    so the search row matches what the artist page shows."""
    artist_id = artist_hit.get("artist_id")
    if artist_id:
        cached = supabase_service.find_artist_by_genius_id(artist_id)
        if cached and cached.get("image_url"):
            return {**artist_hit, "thumbnail": cached["image_url"]}

    name = artist_hit.get("name", "")
    if name:
        deezer_match = await deezer_service.search_artist_by_name(name)
        if deezer_match:
            photo = deezer_match.get("picture_xl") or deezer_match.get("picture_big")
            if photo:
                return {**artist_hit, "thumbnail": photo}
    return artist_hit


def _merge_album_sources(cached_albums: list[dict], deezer_albums: list[dict]) -> list[dict]:
    """Merge cached (Genius-linked) and Deezer album search results.
    Cached albums appear first (they have Claude analyses available for their tracks).
    Deezer entries are deduped against cached ones by case-insensitive title + artist match."""
    def key(name: str, artist: str) -> str:
        return f"{(name or '').strip().lower()}|{(artist or '').strip().lower()}"

    merged: list[dict] = []
    seen: set[str] = set()

    for a in cached_albums:
        name = a.get("name", "")
        k = key(name, a.get("artist", ""))
        if k in seen:
            continue
        seen.add(k)
        merged.append({
            "album_id": a["album_id"],
            "name": name,
            "artist": a.get("artist", ""),
            "thumbnail": a.get("thumbnail"),
            "source": "cached",
        })

    for a in deezer_albums:
        title = a.get("title", "")
        k = key(title, a.get("artist", ""))
        if k in seen:
            continue
        seen.add(k)
        merged.append({
            "album_id": a["deezer_id"],
            "name": title,
            "artist": a.get("artist", ""),
            "thumbnail": a.get("cover_url"),
            "source": "deezer",
        })

    return merged


@router.get("/songs/search")
async def search_suggestions(q: str = Query(..., min_length=1, max_length=200)):
    # Fire Genius, cached albums, and live Deezer album search in parallel.
    genius_task = genius_service.search_songs(q)
    deezer_task = deezer_service.search_albums(q, limit=5)
    genius_results, deezer_albums = await asyncio.gather(genius_task, deezer_task)

    enhanced_artists = await asyncio.gather(*(
        _enhance_artist_photo(a) for a in genius_results.get("artists", [])
    ))
    genius_results["artists"] = list(enhanced_artists)

    cached_albums = supabase_service.search_cached_albums(q, limit=5)
    albums = _merge_album_sources(cached_albums, deezer_albums)

    # Lyric-content matches from our analyzed corpus. These carry a `snippet` so the
    # user can see the phrase in context. Merged into the lyrics list ahead of
    # Genius's own lyric-typed hits and deduped by genius_id.
    lyric_matches = supabase_service.search_cached_songs_by_lyric(q, limit=5)
    seen_ids = {m.get("genius_id") for m in lyric_matches if m.get("genius_id")}
    remaining_genius_lyrics = [
        l for l in genius_results.get("lyrics", [])
        if l.get("genius_id") not in seen_ids
    ]
    genius_results["lyrics"] = lyric_matches + remaining_genius_lyrics

    return {**genius_results, "albums": albums}


@router.get("/album/deezer/{deezer_id}")
async def get_deezer_album(deezer_id: int):
    """Fetch a Deezer album's tracklist for the /album/deezer/[id] page."""
    album = await deezer_service.get_album(deezer_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found on Deezer")
    return album


@router.post("/analyze", dependencies=[Depends(rate_limit_dep(5, 5 / 60.0, "analyze"))])
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    cached = supabase_service.find_song(request.title, request.artist)

    if cached:
        song_id = cached["id"]

        # Backfill metadata for songs analyzed before V2 (missing album_id/album_name).
        existing_meta = cached.get("metadata") or {}
        if cached.get("genius_id") and not existing_meta.get("album_id"):
            fresh_meta = await genius_service.get_song_details(cached["genius_id"])
            if fresh_meta and fresh_meta.get("album_id"):
                try:
                    supabase_service.update_song_metadata(song_id, fresh_meta)
                    cached["metadata"] = fresh_meta
                except Exception as exc:
                    logger.warning("Failed to backfill metadata for %s: %s", song_id, exc)

        # Discourse: return whatever's cached (even if stale) and refresh in the
        # background so the response returns immediately. Cuts cached-song load
        # from ~1-3s (Reddit fetch) to ~100ms.
        discourse_row = supabase_service.find_discourse(song_id)
        excerpts = (discourse_row or {}).get("excerpts") or []
        if not discourse_row or not _is_discourse_fresh(discourse_row):
            background_tasks.add_task(
                _refresh_discourse_bg,
                song_id,
                cached.get("genius_id"),
                request.title,
                request.artist,
            )
        return {**_format_cached(cached), "community_commentary": excerpts}

    # New song: fetch lyrics + community context, store, return WITHOUT calling Claude.
    # Deep AI analysis is generated on demand via POST /songs/{id}/deep-analyze.
    genius_data = await genius_service.search_song(request.title, request.artist)
    song_metadata = await genius_service.get_song_details(genius_data["genius_id"])
    # Album-art priority: Genius album cover > Deezer track cover > Genius song_art (last resort).
    # song_art_image_url is often unrelated user-uploaded promo art, so we only use it
    # when nothing more reliable is available.
    if not song_metadata.get("album_art_url"):
        deezer_cover = await deezer_service.search_track_cover(request.title, request.artist)
        if deezer_cover:
            song_metadata["album_art_url"] = deezer_cover
    if not song_metadata.get("album_art_url"):
        song_metadata["album_art_url"] = song_metadata.get("song_art_fallback_url")
    song_metadata.pop("song_art_fallback_url", None)

    # Best-effort accent color from the album art for the themed song page background.
    if song_metadata.get("album_art_url"):
        song_metadata["accent_color"] = await color_service.extract_dominant_color(
            song_metadata["album_art_url"]
        )
    lyrics = await genius_service.fetch_lyrics(genius_data["url"])
    excerpts = await discourse_service.fetch_discourse(
        genius_data.get("genius_id"), request.title, request.artist
    )
    song = supabase_service.store_song(
        request.title, request.artist, lyrics, genius_data.get("genius_id"), metadata=song_metadata
    )
    try:
        supabase_service.store_discourse(song["id"], excerpts)
    except Exception as exc:
        logger.warning("Failed to persist discourse: %s", exc)

    return {
        "id": song["id"],
        "title": song["title"],
        "artist": song["artist"],
        "lyrics": song["lyrics"],
        "genius_id": song.get("genius_id"),
        "created_at": song.get("created_at"),
        "interpretation": None,
        "community_commentary": excerpts,
        "metadata": song_metadata,
    }


@router.get("/song/{song_id}")
async def get_song(song_id: str):
    song = supabase_service.get_song_by_id(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return _format_cached(song)


@router.get("/song/{song_id}/similar", response_model=list[SimilarSong])
async def get_similar(song_id: str, limit: int = Query(default=3, ge=1, le=10)):
    """Return analyzed songs sharing themes/tone with `song_id`, ranked by score."""
    return supabase_service.find_similar_songs(song_id, limit=limit)


@router.post(
    "/songs/{song_id}/deep-analyze",
    dependencies=[Depends(rate_limit_dep(3, 3 / 60.0, "deep"))],
)
async def deep_analyze(song_id: str):
    """Generate (or return existing) Claude interpretation for a stored song."""
    song = supabase_service.get_song_by_id(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Return cached interpretation if it already exists
    existing = (song.get("interpretations") or [{}])[0].get("content") if song.get("interpretations") else None
    if existing:
        formatted = _format_cached(song)
        discourse_row = supabase_service.find_discourse(song_id)
        excerpts = discourse_row["excerpts"] if discourse_row else []
        return {**formatted, "community_commentary": excerpts}

    # Budget gate — Lyriq is a free hobby project with a monthly Claude cap.
    # Return 402 (Payment Required) with a friendly detail + reset date so the
    # frontend can render a warm degraded state instead of a raw error.
    if not claude_budget.within_budget():
        return JSONResponse(
            status_code=402,
            content={
                "detail": (
                    "Lyriq's monthly analysis budget is out. "
                    "Existing analyses still work — new ones resume on the 1st."
                ),
                "resets_on": claude_budget.reset_date_iso(),
            },
        )

    # Need to generate — pull discourse for context
    discourse_row = supabase_service.find_discourse(song_id)
    excerpts = discourse_row["excerpts"] if discourse_row else []

    interpretation, model_version = await anthropic_service.generate_interpretation(
        song["title"], song["artist"], song["lyrics"], discourse=excerpts
    )
    supabase_service.store_interpretation(song_id, interpretation, model_version)

    return {
        "id": song["id"],
        "title": song["title"],
        "artist": song["artist"],
        "lyrics": song["lyrics"],
        "genius_id": song.get("genius_id"),
        "created_at": song.get("created_at"),
        "interpretation": interpretation,
        "community_commentary": excerpts,
        "metadata": song.get("metadata"),
    }


@router.get("/songs/trending")
async def trending(limit: int = Query(default=10, ge=1, le=50)):
    return supabase_service.get_trending(limit)


@router.get("/songs/billboard")
async def billboard_chart(limit: int = Query(default=10, ge=1, le=100)):
    return await billboard_service.get_hot_100(limit)


@router.get("/news")
async def news(limit: int = Query(default=8, ge=1, le=20)):
    return await news_service.get_music_news(limit)


@router.get("/trending/themes")
async def trending_themes(limit: int = Query(default=5, ge=1, le=20)):
    return supabase_service.get_trending_themes(limit)


@router.get("/songs/by-theme")
async def songs_by_theme(
    theme: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List analyzed songs in the corpus tagged with the given theme."""
    return supabase_service.find_songs_by_theme(theme, limit)


@router.get("/album/{album_id}", response_model=AlbumResponse)
async def get_album(album_id: str):
    album = await _resolve_album(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    return await _hydrate_album_extras(album)


async def _hydrate_artist(genius_artist_id: int) -> Optional[dict]:
    """Fetch artist data from Genius + Deezer and store in our DB."""
    genius_data = await genius_service.get_artist_details(genius_artist_id)
    if not genius_data or not (genius_data.get("name") or "").strip():
        return None
    top_songs = await genius_service.get_artist_top_songs(genius_artist_id, limit=10)

    deezer_artist = await deezer_service.search_artist_by_name(genius_data["name"])
    deezer_id = (deezer_artist or {}).get("id")
    top_albums = []
    image_url = genius_data.get("image_url")
    if deezer_id:
        top_albums = await deezer_service.get_artist_albums(deezer_id, limit=6)
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
        "description_full": genius_data.get("description_full"),
        "top_songs": top_songs,
        "top_albums": top_albums,
    }
    return supabase_service.store_artist(row)


async def _resolve_artist(artist_id: str) -> Optional[dict]:
    if _UUID_RE.match(artist_id):
        return supabase_service.get_artist_by_id(artist_id)

    try:
        genius_id_int = int(artist_id)
    except ValueError:
        return None

    cached = supabase_service.find_artist_by_genius_id(genius_id_int)
    if cached:
        return cached

    return await _hydrate_artist(genius_id_int)


@router.get("/artist/by-name/{name}")
async def lookup_artist_by_name(name: str):
    """Resolve an artist name → Genius artist ID. Used by Billboard rows."""
    genius_id = await genius_service.search_artist_id_by_name(name)
    if not genius_id:
        raise HTTPException(status_code=404, detail="Artist not found")
    return {"genius_id": genius_id}


@router.get("/artist/{artist_id}", response_model=ArtistResponse)
async def get_artist(artist_id: str):
    artist = await _resolve_artist(artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    return artist


@router.post("/admin/reanalyze-all")
async def reanalyze_all(limit: int = Query(default=1000, ge=1, le=10000)):
    """One-off: re-run Claude analysis for every stored song under the current model
    and prompt. Used after prompt/model changes to keep the DB consistent. Skips songs
    whose lyrics aren't stored. Stops if the monthly budget is exhausted."""
    songs = supabase_service.list_songs_with_interpretations(limit=limit)
    updated = 0
    skipped_no_lyrics = 0
    skipped_budget = 0
    for song in songs:
        if not song.get("lyrics"):
            skipped_no_lyrics += 1
            continue
        if not claude_budget.within_budget():
            skipped_budget += 1
            continue
        discourse_row = supabase_service.find_discourse(song["id"])
        excerpts = discourse_row["excerpts"] if discourse_row else []
        try:
            interpretation, model_version = await anthropic_service.generate_interpretation(
                song["title"], song["artist"], song["lyrics"], discourse=excerpts
            )
            supabase_service.store_interpretation(song["id"], interpretation, model_version)
            updated += 1
        except Exception as exc:
            logger.warning("Re-analysis failed for song %s: %s", song["id"], exc)
    return {
        "updated": updated,
        "skipped_no_lyrics": skipped_no_lyrics,
        "skipped_budget": skipped_budget,
        "remaining_budget_usd": round(claude_budget.remaining_usd(), 2),
    }


@router.post("/admin/backfill-accent-colors")
async def backfill_accent_colors(limit: int = Query(default=1000, ge=1, le=10000)):
    """One-off: extract an accent color from album art for every stored song that
    doesn't have one yet. Frontend uses accent_color to tint each song page."""
    songs = supabase_service.list_songs_needing_accent_color(limit=limit)
    updated = 0
    failed = 0
    for song in songs:
        metadata = song.get("metadata") or {}
        art_url = metadata.get("album_art_url")
        if not art_url:
            continue
        color = await color_service.extract_dominant_color(art_url)
        if not color:
            failed += 1
            continue
        try:
            supabase_service.update_song_metadata(song["id"], {**metadata, "accent_color": color})
            updated += 1
        except Exception as exc:
            logger.warning("Accent color update failed for song %s: %s", song["id"], exc)
            failed += 1
    return {"updated": updated, "failed": failed, "scanned": len(songs)}
