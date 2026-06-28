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
