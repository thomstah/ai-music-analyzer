import logging
import re
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

DEEZER_API_BASE = "https://api.deezer.com"


async def search_artist_by_name(name: str) -> Optional[dict]:
    """Search Deezer for an artist by name. Returns the first hit or None."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{DEEZER_API_BASE}/search/artist",
                params={"q": name, "limit": 1},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError):
        return None
    hits = data.get("data") or []
    if not hits:
        return None
    return hits[0]


async def search_track_cover(title: str, artist: str) -> Optional[str]:
    """Search Deezer for a track, return its album cover URL (medium size) or None."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{DEEZER_API_BASE}/search/track",
                params={"q": f"{title} {artist}", "limit": 1},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError):
        return None
    hits = data.get("data") or []
    if not hits:
        return None
    album = hits[0].get("album") or {}
    return album.get("cover_big") or album.get("cover_medium")


async def search_albums(query: str, limit: int = 5) -> list[dict]:
    """Search Deezer for albums by free-text query. Returned shape:
    [{deezer_id, title, artist, cover_url, release_year}]"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{DEEZER_API_BASE}/search/album",
                params={"q": query, "limit": limit},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError):
        return []
    hits = data.get("data") or []
    results = []
    for a in hits:
        artist = a.get("artist") or {}
        results.append({
            "deezer_id": a.get("id"),
            "title": a.get("title", ""),
            "artist": artist.get("name", ""),
            "cover_url": a.get("cover_xl") or a.get("cover_big") or a.get("cover_medium"),
            "release_year": None,  # album search results don't include release date
        })
    return results


async def get_album(deezer_album_id: int) -> Optional[dict]:
    """Fetch a Deezer album's full details + tracklist. Returned shape:
    {deezer_id, title, artist, cover_url, release_year, tracks: [{deezer_id, title, artist_name}]}"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{DEEZER_API_BASE}/album/{deezer_album_id}")
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError):
        return None
    if data.get("error"):
        return None

    artist = data.get("artist") or {}
    release_date = data.get("release_date", "") or ""
    year_match = re.search(r"^(\d{4})", release_date)
    tracks_block = data.get("tracks") or {}
    raw_tracks = tracks_block.get("data") or []
    tracks = []
    for t in raw_tracks:
        t_artist = t.get("artist") or {}
        tracks.append({
            "deezer_id": t.get("id"),
            "title": t.get("title", ""),
            "artist_name": t_artist.get("name") or artist.get("name", ""),
        })
    return {
        "deezer_id": data.get("id"),
        "title": data.get("title", ""),
        "artist": artist.get("name", ""),
        "cover_url": data.get("cover_xl") or data.get("cover_big"),
        "release_year": year_match.group(1) if year_match else None,
        "tracks": tracks,
    }


async def get_artist_albums(deezer_artist_id: int, limit: int = 6) -> list[dict]:
    """Fetch the artist's full-album discography from Deezer, excluding singles/EPs.
    Returned shape: [{album_id_deezer, title, cover_url, release_year, fans}]"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{DEEZER_API_BASE}/artist/{deezer_artist_id}/albums",
                params={"limit": 50},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError):
        return []
    raw = data.get("data") or []
    albums = []
    for a in raw:
        if a.get("record_type") != "album":
            continue
        release_date = a.get("release_date", "") or ""
        year_match = re.search(r"^(\d{4})", release_date)
        albums.append({
            "album_id_deezer": a.get("id"),
            "title": a.get("title", ""),
            "cover_url": a.get("cover_xl") or a.get("cover_big"),
            "release_year": year_match.group(1) if year_match else None,
            "fans": a.get("fans", 0),
        })
        if len(albums) >= limit:
            break
    return albums
