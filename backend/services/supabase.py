import logging
import time
from supabase import create_client, Client
from config import settings
from typing import Optional

logger = logging.getLogger(__name__)

_trending_themes_cache: dict = {"data": None, "fetched_at": 0.0}
_TRENDING_THEMES_TTL = 300.0  # 5 minutes


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


def update_song_metadata(song_id: str, metadata: dict) -> None:
    """Backfill metadata for an existing song row (e.g., songs analyzed pre-V2)."""
    if not metadata:
        return
    client = get_client()
    client.table("songs").update({"metadata": metadata}).eq("id", song_id).execute()


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


def list_songs_with_interpretations(limit: int = 1000) -> list[dict]:
    """List songs that have at least one stored interpretation. Used by the one-off
    `/admin/reanalyze-all` backfill to regenerate interpretations under a new prompt
    or model."""
    client = get_client()
    result = (
        client.table("songs")
        .select("id, title, artist, lyrics, interpretations!inner(id)")
        .limit(limit)
        .execute()
    )
    return result.data or []


def list_songs_needing_accent_color(limit: int = 1000) -> list[dict]:
    """List songs that have album_art_url in metadata but no accent_color yet.
    Used by `/admin/backfill-accent-colors`."""
    client = get_client()
    result = (
        client.table("songs")
        .select("id, metadata")
        .not_.is_("metadata", "null")
        .limit(limit)
        .execute()
    )
    matches = []
    for row in result.data or []:
        meta = row.get("metadata") or {}
        if meta.get("album_art_url") and not meta.get("accent_color"):
            matches.append(row)
    return matches


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
    now = time.time()
    if (
        _trending_themes_cache["data"] is not None
        and now - _trending_themes_cache["fetched_at"] < _TRENDING_THEMES_TTL
    ):
        return _trending_themes_cache["data"][:limit]

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
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    aggregated = [{"theme": t, "count": c} for t, c in top]
    _trending_themes_cache["data"] = aggregated
    _trending_themes_cache["fetched_at"] = now
    return aggregated[:limit]


def find_songs_by_theme(theme: str, limit: int = 20) -> list[dict]:
    """Return songs whose interpretation contains the given theme tag.

    Case-insensitive match. Uses Python-side filtering against the interpretations
    table for MVP simplicity; revisit if the table grows past ~10k rows.
    """
    theme_normalized = theme.strip().lower()
    if not theme_normalized:
        return []

    client = get_client()
    result = (
        client.table("interpretations")
        .select("content, songs(id, title, artist, metadata)")
        .limit(10000)
        .execute()
    )
    matches: list[dict] = []
    seen_song_ids: set[str] = set()
    for row in result.data or []:
        content = row.get("content") or {}
        themes = content.get("themes") or []
        normalized = [t.strip().lower() for t in themes if isinstance(t, str)]
        if theme_normalized not in normalized:
            continue
        song = row.get("songs") or {}
        song_id = song.get("id")
        if not song_id or song_id in seen_song_ids:
            continue
        seen_song_ids.add(song_id)
        matches.append({
            "id": song_id,
            "title": song.get("title", ""),
            "artist": song.get("artist", ""),
            "metadata": song.get("metadata"),
            "tldr": content.get("tldr"),
        })
        if len(matches) >= limit:
            break
    return matches


def find_album(genius_album_id: int) -> Optional[dict]:
    client = get_client()
    result = (
        client.table("albums")
        .select("*")
        .eq("genius_id", genius_album_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def store_album(album_data: dict) -> dict:
    client = get_client()
    result = client.table("albums").upsert(album_data, on_conflict="genius_id").execute()
    return result.data[0]


def get_album_by_id(album_id: str) -> Optional[dict]:
    client = get_client()
    result = (
        client.table("albums")
        .select("*")
        .eq("id", album_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def find_artist_by_genius_id(genius_artist_id: int) -> Optional[dict]:
    client = get_client()
    result = (
        client.table("artists")
        .select("*")
        .eq("genius_id", genius_artist_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def store_artist(artist_data: dict) -> dict:
    client = get_client()
    result = client.table("artists").upsert(artist_data, on_conflict="genius_id").execute()
    if not result.data:
        raise RuntimeError("Failed to insert artist: no data returned")
    return result.data[0]


def get_artist_by_id(artist_id: str) -> Optional[dict]:
    client = get_client()
    result = (
        client.table("artists")
        .select("*")
        .eq("id", artist_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def search_cached_albums(query: str, limit: int = 5) -> list[dict]:
    """Find albums whose name, song title, or artist matches the query.

    Runs two queries (one on songs by title/artist, one on songs by album_name
    inside metadata JSONB), merges results, deduplicates by album_id.
    """
    # Strip characters that would break the PostgREST or_ filter syntax.
    safe_query = "".join(c for c in query if c not in '",()').strip()
    if not safe_query:
        return []
    client = get_client()
    pattern = f"%{safe_query}%"

    songs_match = (
        client.table("songs")
        .select("metadata, artist, created_at")
        .or_(f'title.ilike."{pattern}",artist.ilike."{pattern}"')
        .not_.is_("metadata", "null")
        .order("created_at")
        .limit(50)
        .execute()
    )

    # Separate query for albums whose name (in JSONB metadata) matches.
    # JSONB key filter via PostgREST: metadata->>album_name
    albums_match = (
        client.table("songs")
        .select("metadata, artist, created_at")
        .ilike("metadata->>album_name", pattern)
        .order("created_at")
        .limit(50)
        .execute()
    )

    result = type("MergedResult", (), {
        "data": (songs_match.data or []) + (albums_match.data or [])
    })()
    seen: set[int] = set()
    albums: list[dict] = []
    for row in result.data or []:
        meta = row.get("metadata") or {}
        album_id = meta.get("album_id")
        album_name = meta.get("album_name")
        if not album_id or not album_name or album_id in seen:
            continue
        seen.add(album_id)
        albums.append({
            "album_id": album_id,
            "name": album_name,
            "artist": row.get("artist", ""),
            "thumbnail": meta.get("album_art_url"),
        })
        if len(albums) >= limit:
            break
    return albums
