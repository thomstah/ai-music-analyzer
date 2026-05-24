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
    return result.data[0] if result.data else None


def store_song(title: str, artist: str, lyrics: str, genius_id: Optional[int] = None) -> dict:
    client = get_client()
    result = (
        client.table("songs")
        .insert({"title": title, "artist": artist, "lyrics": lyrics, "genius_id": genius_id})
        .execute()
    )
    return result.data[0]


def store_interpretation(song_id: str, content: dict, model_version: str) -> dict:
    client = get_client()
    result = (
        client.table("interpretations")
        .insert({"song_id": song_id, "content": content, "model_version": model_version})
        .execute()
    )
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
