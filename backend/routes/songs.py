from fastapi import APIRouter, HTTPException, Query
from models.schemas import AnalyzeRequest
import services.supabase as supabase_service
import services.genius as genius_service
import services.anthropic as anthropic_service

router = APIRouter()


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
        return _format_cached(cached)

    genius_data = await genius_service.search_song(request.title, request.artist)
    lyrics = await genius_service.fetch_lyrics(genius_data["url"])
    interpretation, model_version = await anthropic_service.generate_interpretation(
        request.title, request.artist, lyrics
    )

    song = supabase_service.store_song(
        request.title, request.artist, lyrics, genius_data.get("genius_id")
    )
    supabase_service.store_interpretation(song["id"], interpretation, model_version)

    return {
        "id": song["id"],
        "title": song["title"],
        "artist": song["artist"],
        "lyrics": song["lyrics"],
        "genius_id": song.get("genius_id"),
        "created_at": song.get("created_at"),
        "interpretation": interpretation,
    }


@router.get("/song/{song_id}")
async def get_song(song_id: str):
    song = supabase_service.get_song_by_id(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return _format_cached(song)
