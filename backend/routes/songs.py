import asyncio
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Query
from models.schemas import AnalyzeRequest
import services.supabase as supabase_service
import services.genius as genius_service
import services.anthropic as anthropic_service
import services.discourse as discourse_service
import services.billboard as billboard_service
import services.news as news_service

logger = logging.getLogger(__name__)

router = APIRouter()

DISCOURSE_TTL_DAYS = 7


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
    return await genius_service.search_songs(q)


@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    cached = supabase_service.find_song(request.title, request.artist)

    if cached:
        song_id = cached["id"]
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
