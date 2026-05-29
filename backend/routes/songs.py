from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Query
from models.schemas import AnalyzeRequest
import services.supabase as supabase_service
import services.genius as genius_service
import services.anthropic as anthropic_service
import services.discourse as discourse_service

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
    }


def _is_discourse_fresh(row: dict) -> bool:
    scraped_at = datetime.fromisoformat(row["scraped_at"].replace("Z", "+00:00"))
    return datetime.now(timezone.utc) - scraped_at < timedelta(days=DISCOURSE_TTL_DAYS)


@router.get("/songs/search")
async def search_cache(title: str = Query(...), artist: str = Query(...)):
    song = supabase_service.find_song(title, artist)
    if not song:
        return {"found": False, "song": None}
    return {"found": True, "song": _format_cached(song)}


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
            supabase_service.store_discourse(song_id, excerpts)
        return {**_format_cached(cached), "community_commentary": excerpts}

    genius_data = await genius_service.search_song(request.title, request.artist)
    lyrics = await genius_service.fetch_lyrics(genius_data["url"])
    excerpts = await discourse_service.fetch_discourse(
        genius_data.get("genius_id"), request.title, request.artist
    )
    interpretation, model_version = await anthropic_service.generate_interpretation(
        request.title, request.artist, lyrics, discourse=excerpts
    )
    song = supabase_service.store_song(
        request.title, request.artist, lyrics, genius_data.get("genius_id")
    )
    supabase_service.store_interpretation(song["id"], interpretation, model_version)
    supabase_service.store_discourse(song["id"], excerpts)

    return {
        "id": song["id"],
        "title": song["title"],
        "artist": song["artist"],
        "lyrics": song["lyrics"],
        "genius_id": song.get("genius_id"),
        "created_at": song.get("created_at"),
        "interpretation": interpretation,
        "community_commentary": excerpts,
    }


@router.get("/song/{song_id}")
async def get_song(song_id: str):
    song = supabase_service.get_song_by_id(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return _format_cached(song)
