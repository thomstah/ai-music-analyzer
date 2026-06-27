import logging
import httpx
from datetime import datetime, timezone, timedelta
from config import settings

logger = logging.getLogger(__name__)

NEWS_API_BASE = "https://newsapi.org/v2"
MUSIC_SOURCES = "pitchfork.com,rollingstone.com,nme.com,billboard.com,stereogum.com"

_cache: dict = {"data": None, "fetched_at": None}
_CACHE_TTL = timedelta(hours=1)


async def get_music_news(limit: int = 8) -> list[dict]:
    now = datetime.now(timezone.utc)
    if (
        _cache["data"] is not None
        and _cache["fetched_at"] is not None
        and now - _cache["fetched_at"] < _CACHE_TTL
    ):
        return _cache["data"][:limit]

    if not settings.newsapi_key:
        return []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{NEWS_API_BASE}/everything",
                params={
                    "q": "music",
                    "domains": MUSIC_SOURCES,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": 20,
                    "apiKey": settings.newsapi_key,
                },
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.warning("NewsAPI fetch failed: %s", exc)
        return _cache["data"][:limit] if _cache["data"] else []

    if data.get("status") != "ok":
        return _cache["data"][:limit] if _cache["data"] else []

    articles = [
        {
            "title": a.get("title", ""),
            "description": a.get("description", ""),
            "url": a.get("url", ""),
            "image_url": a.get("urlToImage"),
            "source": (a.get("source") or {}).get("name", ""),
            "published_at": a.get("publishedAt", ""),
        }
        for a in data.get("articles", [])
        if a.get("title") and a.get("url")
    ]

    if articles:
        _cache["data"] = articles
        _cache["fetched_at"] = now

    return articles[:limit]
