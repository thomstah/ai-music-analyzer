import re
import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException
from config import settings

GENIUS_API_BASE = "https://api.genius.com"


async def search_song(title: str, artist: str) -> dict:
    query = f"{title} {artist}"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GENIUS_API_BASE}/search",
            params={"q": query},
            headers={"Authorization": f"Bearer {settings.genius_access_token}"},
        )
        response.raise_for_status()

    hits = response.json()["response"]["hits"]
    if not hits:
        raise HTTPException(status_code=404, detail=f"Song '{title}' by '{artist}' not found on Genius")

    hit = hits[0]["result"]
    return {"url": hit["url"], "genius_id": hit["id"]}


async def fetch_lyrics(url: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url)

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not extract lyrics from Genius")

    soup = BeautifulSoup(response.text, "html.parser")
    containers = soup.find_all("div", attrs={"data-lyrics-container": "true"})

    if not containers:
        raise HTTPException(status_code=502, detail="Could not extract lyrics from Genius")

    parts = []
    for container in containers:
        for br in container.find_all("br"):
            br.replace_with("\n")
        parts.append(container.get_text())

    return normalize_lyrics("\n".join(parts))


def normalize_lyrics(lyrics: str) -> str:
    cleaned = re.sub(r"\[.*?\]", "", lyrics)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
