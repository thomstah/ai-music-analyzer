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


async def search_songs(query: str, limit: int = 8) -> list[dict]:
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
        return []

    hits = data["response"]["hits"][:limit]
    return [
        {
            "title": h["result"]["title"],
            "artist": h["result"]["primary_artist"]["name"],
            "genius_id": h["result"]["id"],
            "thumbnail": h["result"].get("song_art_image_thumbnail_url"),
        }
        for h in hits
        if h.get("type") == "song"
    ]


def normalize_lyrics(lyrics: str) -> str:
    # Strip Genius UI boilerplate: e.g. "67 ContributorsTranslations...Lyrics"
    cleaned = re.sub(r"\d+\s*Contributor\w*[^\n]*\n?", "", lyrics)
    cleaned = re.sub(r"\[.*?\]", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
