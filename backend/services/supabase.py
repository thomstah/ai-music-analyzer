import logging
from supabase import create_client, Client
from config import settings
from typing import Optional

logger = logging.getLogger(__name__)


def get_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)


def find_song(title: str, artist: str) -> Optional[dict]:
    client = get_client()
    result = (
        client.table("songs")
        .select("*, interpretations(*)")
        .ilike("title", title)
        .ilike("artist", artist)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    song = result.data[0]
    try:
        client.table("songs").update({"request_count": song.get("request_count", 0) + 1}).eq("id", song["id"]).execute()
    except Exception as exc:
        logger.warning("Failed to increment request_count for song %s: %s", song["id"], exc)
    return song


def store_song(title: str, artist: str, lyrics: str, genius_id: Optional[int] = None, metadata: Optional[dict] = None) -> dict:
    client = get_client()
    data = {"title": title, "artist": artist, "lyrics": lyrics}
    if genius_id is not None:
        data["genius_id"] = genius_id
    # Skip persisting metadata when fetch failed (empty dict). Non-empty dicts with
    # all-None values still persist, so the song row has a metadata column we can
    # backfill later.
    if metadata:
        data["metadata"] = metadata
    result = client.table("songs").insert(data).execute()
    if not result.data:
        raise RuntimeError("Failed to insert song: no data returned")
    return result.data[0]


def store_interpretation(song_id: str, content: dict, model_version: str) -> dict:
    client = get_client()
    result = (
        client.table("interpretations")
        .insert({"song_id": song_id, "content": content, "model_version": model_version})
        .execute()
    )
    if not result.data:
        raise RuntimeError("Failed to insert interpretation: no data returned")
    return result.data[0]


def get_song_by_id(song_id: str) -> Optional[dict]:
    client = get_client()
    result = (
        client.table("songs")
        .select("*, interpretations(*)")
        .eq("id", song_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def find_discourse(song_id: str) -> Optional[dict]:
    client = get_client()
    result = (
        client.table("discourse")
        .select("*")
        .eq("song_id", song_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_trending(limit: int = 10) -> list[dict]:
    client = get_client()
    result = (
        client.table("songs")
        .select("id, title, artist, request_count")
        .order("request_count", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def store_discourse(song_id: str, excerpts: list[dict]) -> dict:
    client = get_client()
    client.table("discourse").delete().eq("song_id", song_id).execute()
    result = (
        client.table("discourse")
        .insert({"song_id": song_id, "excerpts": excerpts})
        .execute()
    )
    if not result.data:
        raise RuntimeError("Failed to insert discourse: no data returned")
    return result.data[0]


def get_trending_themes(limit: int = 5) -> list[dict]:
    client = get_client()
    # Pull interpretations and aggregate in Python. For MVP-scale DB this is fine;
    # revisit if the table grows past ~10k rows.
    result = client.table("interpretations").select("content").limit(10000).execute()
    counts: dict[str, int] = {}
    for row in result.data or []:
        themes = (row.get("content") or {}).get("themes") or []
        for theme in themes:
            if isinstance(theme, str) and theme.strip():
                key = theme.strip().lower()
                counts[key] = counts.get(key, 0) + 1
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return [{"theme": t, "count": c} for t, c in top]
