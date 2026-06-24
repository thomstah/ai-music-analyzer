import re
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
    except (httpx.HTTPStatusError, httpx.RequestError):
        return {}

    album = song.get("album") or {}
    release_date = album.get("release_date_for_display", "") or song.get("release_date_for_display", "")
    release_year = release_date.split()[-1] if release_date else None

    producers = song.get("producer_artists", [])
    producer = producers[0]["name"] if producers else None

    return {
        "album_art_url": song.get("song_art_image_url"),
        "album_name": album.get("name"),
        "release_year": release_year,
        "producer": producer,
    }


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
