from supabase import create_client, Client
from config import settings
from typing import Optional


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
    client.table("songs").update({"request_count": song.get("request_count", 0) + 1}).eq("id", song["id"]).execute()
    return song


def store_song(title: str, artist: str, lyrics: str, genius_id: Optional[int] = None) -> dict:
    client = get_client()
    result = (
        client.table("songs")
        .insert({"title": title, "artist": artist, "lyrics": lyrics, "genius_id": genius_id})
        .execute()
    )
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
    return result.data


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
