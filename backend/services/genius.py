import re
from typing import Optional
import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException
from config import settings

GENIUS_API_BASE = "https://api.genius.com"


async def search_song(title: str, artist: str) -> dict:
    query = f"{title} {artist}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GENIUS_API_BASE}/search",
                params={"q": query},
                headers={"Authorization": f"Bearer {settings.genius_access_token}"},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Genius API request failed")

    hits = data["response"]["hits"]
    if not hits:
        raise HTTPException(status_code=404, detail=f"Song '{title}' by '{artist}' not found on Genius")

    artist_lower = artist.lower()
    hit = next(
        (h["result"] for h in hits
         if artist_lower in h["result"].get("primary_artist", {}).get("name", "").lower()),
        hits[0]["result"],
    )
    return {"url": hit["url"], "genius_id": hit["id"]}


async def fetch_lyrics(url: str) -> str:
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Could not extract lyrics from Genius")

    soup = BeautifulSoup(html, "html.parser")
    containers = soup.find_all("div", attrs={"data-lyrics-container": "true"})

    if not containers:
        raise HTTPException(status_code=502, detail="Could not extract lyrics from Genius")

    parts = []
    for container in containers:
        for br in container.find_all("br"):
            br.replace_with("\n")
        parts.append(container.get_text())

    return normalize_lyrics("\n".join(parts))


async def search_songs(query: str, limit: int = 10) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GENIUS_API_BASE}/search",
                params={"q": query},
                headers={"Authorization": f"Bearer {settings.genius_access_token}"},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError):
        return {"songs": [], "lyrics": [], "artists": []}

    query_words = {w for w in query.lower().split() if len(w) > 1}
    songs: list[dict] = []
    lyrics: list[dict] = []
    seen_song_ids: set[int] = set()
    seen_artist_ids: set[int] = set()
    artists: list[dict] = []

    for h in data["response"]["hits"][:limit]:
        result = h.get("result", {})
        song_id = result.get("id")
        if not song_id or song_id in seen_song_ids:
            continue
        seen_song_ids.add(song_id)

        primary_artist = result.get("primary_artist", {})
        # Skip Genius translation/romanization accounts (e.g. "Genius Brasil Traduções",
        # "Genius traductions françaises") — these are translated versions, not original songs.
        if primary_artist.get("name", "").lower().startswith("genius "):
            continue

        entry = {
            "title": result.get("title", ""),
            "artist": primary_artist.get("name", ""),
            "genius_id": song_id,
            "thumbnail": result.get("song_art_image_thumbnail_url"),
        }

        if h.get("type") == "lyric":
            lyrics.append(entry)
        else:
            songs.append(entry)

        artist_id = primary_artist.get("id")
        if artist_id and artist_id not in seen_artist_ids:
            artist_name_lower = primary_artist.get("name", "").lower()
            if query_words and any(w in artist_name_lower for w in query_words):
                seen_artist_ids.add(artist_id)
                artists.append({
                    "name": primary_artist.get("name", ""),
                    "artist_id": artist_id,
                    "thumbnail": primary_artist.get("image_url"),
                })

    return {"songs": songs[:8], "lyrics": lyrics[:5], "artists": artists[:3]}


async def get_song_details(genius_id: int) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GENIUS_API_BASE}/songs/{genius_id}",
                params={"text_format": "plain"},
                headers={"Authorization": f"Bearer {settings.genius_access_token}"},
            )
            response.raise_for_status()
            song = response.json()["response"]["song"]
    except (httpx.HTTPStatusError, httpx.RequestError, KeyError, ValueError):
        return {}

    album = song.get("album") or {}
    release_date = album.get("release_date_for_display", "") or song.get("release_date_for_display", "")
    year_match = re.search(r"\b(\d{4})\b", release_date) if release_date else None
    release_year = year_match.group(1) if year_match else None

    producers = song.get("producer_artists", [])
    producer = producers[0]["name"] if producers else None

    return {
        "artist_id": (song.get("primary_artist") or {}).get("id"),
        "album_id": album.get("id"),
        "album_art_url": song.get("song_art_image_url"),
        "album_name": album.get("name"),
        "release_year": release_year,
        "producer": producer,
    }


async def get_album_details(album_id: int) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            album_resp = await client.get(
                f"{GENIUS_API_BASE}/albums/{album_id}",
                params={"text_format": "plain"},
                headers={"Authorization": f"Bearer {settings.genius_access_token}"},
            )
            album_resp.raise_for_status()
            album = album_resp.json()["response"]["album"]

            tracks_resp = await client.get(
                f"{GENIUS_API_BASE}/albums/{album_id}/tracks",
                params={"text_format": "plain", "per_page": 50},
                headers={"Authorization": f"Bearer {settings.genius_access_token}"},
            )
            tracks_resp.raise_for_status()
            # Genius returns response.tracks[].song, NOT response.songs[]
            tracks_data = tracks_resp.json()["response"].get("tracks", [])
    except (httpx.HTTPStatusError, httpx.RequestError, KeyError, ValueError):
        return {}

    release_date = album.get("release_date_for_display", "")
    year_match = re.search(r"\b(\d{4})\b", release_date) if release_date else None
    release_year = year_match.group(1) if year_match else None

    producers: list[str] = []
    for group in album.get("performance_groups") or []:
        if (group.get("label") or "").lower() == "producer":
            for artist in group.get("artists") or []:
                name = artist.get("name")
                if name and name not in producers:
                    producers.append(name)

    tracklist = []
    for t in tracks_data:
        song = t.get("song") or {}
        if not song.get("id"):
            continue
        tracklist.append({
            "genius_id": song.get("id"),
            "title": song.get("title", ""),
            "thumbnail": song.get("song_art_image_thumbnail_url"),
        })

    return {
        "genius_id": album.get("id"),
        "artist_id": (album.get("artist") or {}).get("id"),
        "title": album.get("name", ""),
        "artist": (album.get("artist") or {}).get("name", ""),
        "release_year": release_year,
        "cover_art_url": album.get("cover_art_url"),
        "producers": producers,
        "tracklist": tracklist,
    }


async def get_artist_details(artist_id: int) -> dict:
    """Fetch artist bio, header image, alternate names from Genius."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GENIUS_API_BASE}/artists/{artist_id}",
                params={"text_format": "plain"},
                headers={"Authorization": f"Bearer {settings.genius_access_token}"},
            )
            response.raise_for_status()
            artist = response.json()["response"]["artist"]
    except (httpx.HTTPStatusError, httpx.RequestError, KeyError, ValueError):
        return {}

    description = artist.get("description") or {}
    description_preview = ""
    if isinstance(description, dict):
        full = (description.get("plain") or "").strip()
        if full:
            if len(full) > 300:
                # Snap to last whitespace before 300 to avoid mid-word cuts
                snap = full.rfind(" ", 0, 300)
                cut_at = snap if snap > 200 else 300
                description_preview = full[:cut_at].rstrip() + "…"
            else:
                description_preview = full

    return {
        "genius_id": artist.get("id"),
        "name": artist.get("name", ""),
        "alternate_names": artist.get("alternate_names") or [],
        "image_url": artist.get("image_url"),
        "header_image_url": artist.get("header_image_url"),
        "description_preview": description_preview,
    }


async def get_artist_top_songs(artist_id: int, limit: int = 10) -> list[dict]:
    """Fetch the artist's most popular songs on Genius."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GENIUS_API_BASE}/artists/{artist_id}/songs",
                params={"sort": "popularity", "per_page": limit, "text_format": "plain"},
                headers={"Authorization": f"Bearer {settings.genius_access_token}"},
            )
            response.raise_for_status()
            songs = response.json()["response"].get("songs", [])
    except (httpx.HTTPStatusError, httpx.RequestError, KeyError, ValueError):
        return []
    return [
        {
            "genius_id": s.get("id"),
            "title": s.get("title", ""),
            "thumbnail": s.get("song_art_image_thumbnail_url"),
            "artist_name": s.get("primary_artist_names") or s.get("artist_names") or "",
        }
        for s in songs
        if s.get("id")
    ]


async def search_artist_id_by_name(name: str) -> Optional[int]:
    """Find an artist ID by name via Genius search."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GENIUS_API_BASE}/search",
                params={"q": name},
                headers={"Authorization": f"Bearer {settings.genius_access_token}"},
            )
            response.raise_for_status()
            hits = response.json()["response"].get("hits", [])
    except (httpx.HTTPStatusError, httpx.RequestError, KeyError, ValueError):
        return None
    name_lower = name.lower()
    for h in hits:
        primary = (h.get("result") or {}).get("primary_artist") or {}
        if primary.get("id") and name_lower in (primary.get("name") or "").lower():
            return primary["id"]
    # Fall back to first hit's primary artist
    if hits:
        primary = (hits[0].get("result") or {}).get("primary_artist") or {}
        return primary.get("id")
    return None


def normalize_lyrics(lyrics: str) -> str:
    # Strip "67 ContributorsTranslationsFrançais...Song Title Lyrics" boilerplate line
    cleaned = re.sub(r"\d+\s*Contributor[^\n]*\n?", "", lyrics)
    # Strip the Genius "{Title} Lyrics" header — only at the very start, not mid-song
    cleaned = re.sub(r"\A[^\n]*\bLyrics\s*\n?", "", cleaned, count=1)
    # Strip section headers like [Verse 1]
    cleaned = re.sub(r"\[.*?\]", "", cleaned)
    # Collapse excess blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
