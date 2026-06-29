import logging
import re
from typing import Optional
import httpx
from config import settings

logger = logging.getLogger(__name__)

MUSIXMATCH_API_BASE = "https://api.musixmatch.com/ws/1.1"

# The dev tier appends a tracking footer like "******* This Lyrics is NOT for ..."
# Strip everything after the first asterisk-fence so it doesn't appear in the UI.
_TRACKING_FOOTER_RE = re.compile(r"\*{3,}.*$", re.DOTALL)


async def search_track(title: str, artist: str) -> Optional[dict]:
    """Search Musixmatch for a track. Returns the top match's track object or None."""
    if not settings.musixmatch_api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{MUSIXMATCH_API_BASE}/track.search",
                params={
                    "q_track": title,
                    "q_artist": artist,
                    "page_size": 1,
                    "s_track_rating": "desc",
                    "apikey": settings.musixmatch_api_key,
                },
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.warning("Musixmatch search failed: %s", exc)
        return None

    track_list = (data.get("message") or {}).get("body", {}).get("track_list") or []
    if not track_list:
        return None
    return (track_list[0] or {}).get("track")


async def get_lyrics(track_id: int) -> Optional[dict]:
    """Fetch lyrics for a Musixmatch track. Returns dict with snippet + attribution URLs."""
    if not settings.musixmatch_api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{MUSIXMATCH_API_BASE}/track.lyrics.get",
                params={
                    "track_id": track_id,
                    "apikey": settings.musixmatch_api_key,
                },
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.warning("Musixmatch lyrics fetch failed: %s", exc)
        return None

    lyrics_obj = (data.get("message") or {}).get("body", {}).get("lyrics") or {}
    body_text = (lyrics_obj.get("lyrics_body") or "").strip()
    if not body_text:
        return None

    cleaned = _TRACKING_FOOTER_RE.sub("", body_text).strip()
    return {
        "lyrics": cleaned,
        "musixmatch_track_id": track_id,
        "pixel_tracking_url": lyrics_obj.get("pixel_tracking_url"),
    }


async def fetch_lyrics_by_name(title: str, artist: str) -> Optional[dict]:
    """Convenience: search by name, then fetch lyrics + share URL in one call."""
    track = await search_track(title, artist)
    if not track:
        return None
    track_id = track.get("track_id")
    if not track_id:
        return None
    lyrics_data = await get_lyrics(track_id)
    if not lyrics_data:
        return None
    return {
        **lyrics_data,
        "track_share_url": track.get("track_share_url"),
    }
