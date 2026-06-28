import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from models.schemas import AnalyzeRequest, AlbumResponse, ArtistResponse
import services.supabase as supabase_service
import services.genius as genius_service
import services.deezer as deezer_service
import services.anthropic as anthropic_service
import services.discourse as discourse_service
import services.billboard as billboard_service
import services.news as news_service

logger = logging.getLogger(__name__)

router = APIRouter()

DISCOURSE_TTL_DAYS = 7


_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


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

    return supabase_service.store_album(fetched)


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


@router.get("/songs/search")
async def search_suggestions(q: str = Query(..., min_length=1, max_length=200)):
    genius_results = await genius_service.search_songs(q)
    albums = supabase_service.search_cached_albums(q, limit=5)
    return {**genius_results, "albums": albums}


@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
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

        discourse_row = supabase_service.find_discourse(song_id)
        if discourse_row and _is_discourse_fresh(discourse_row):
            excerpts = discourse_row["excerpts"]
        else:
            excerpts = await discourse_service.fetch_discourse(
                cached.get("genius_id"), request.title, request.artist
            )
            try:
                supabase_service.store_discourse(song_id, excerpts)
            except Exception as exc:
                logger.warning("Failed to persist discourse: %s", exc, exc_info=True)
        return {**_format_cached(cached), "community_commentary": excerpts}

    genius_data = await genius_service.search_song(request.title, request.artist)
    song_metadata = await genius_service.get_song_details(genius_data["genius_id"])
    lyrics = await genius_service.fetch_lyrics(genius_data["url"])
    excerpts = await discourse_service.fetch_discourse(
        genius_data.get("genius_id"), request.title, request.artist
    )
    interpretation, model_version = await anthropic_service.generate_interpretation(
        request.title, request.artist, lyrics, discourse=excerpts
    )
    song = supabase_service.store_song(
        request.title, request.artist, lyrics, genius_data.get("genius_id"), metadata=song_metadata
    )
    supabase_service.store_interpretation(song["id"], interpretation, model_version)
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
        "interpretation": interpretation,
        "community_commentary": excerpts,
        "metadata": song_metadata,
    }


@router.get("/song/{song_id}")
async def get_song(song_id: str):
    song = supabase_service.get_song_by_id(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return _format_cached(song)


@router.get("/songs/trending")
async def trending(limit: int = Query(default=10, ge=1, le=50)):
    return supabase_service.get_trending(limit)


@router.get("/songs/billboard")
async def billboard_chart(limit: int = Query(default=10, ge=1, le=100)):
    return await asyncio.to_thread(billboard_service.get_hot_100, limit)


@router.get("/news")
async def news(limit: int = Query(default=8, ge=1, le=20)):
    return await news_service.get_music_news(limit)


@router.get("/trending/themes")
async def trending_themes(limit: int = Query(default=5, ge=1, le=20)):
    return supabase_service.get_trending_themes(limit)


@router.get("/album/{album_id}", response_model=AlbumResponse)
async def get_album(album_id: str):
    album = await _resolve_album(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    return album


async def _hydrate_artist(genius_artist_id: int) -> Optional[dict]:
    """Fetch artist data from Genius + Deezer and store in our DB."""
    genius_data = await genius_service.get_artist_details(genius_artist_id)
    if not genius_data or not genius_data.get("name"):
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
