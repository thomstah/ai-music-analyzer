import asyncio
import logging
from datetime import datetime, timezone, timedelta
import services.deezer as deezer_service

logger = logging.getLogger(__name__)

_cache: dict = {"data": None, "fetched_at": None}
_CACHE_TTL = timedelta(hours=24)


def _fetch_chart_raw(limit: int) -> list[dict]:
    """Sync Billboard scrape. Runs in a thread."""
    import billboard  # type: ignore
    chart = billboard.ChartData("hot-100")
    return [
        {"rank": i + 1, "title": entry.title, "artist": entry.artist}
        for i, entry in enumerate(chart[:limit])
    ]


async def _enrich_with_cover(entry: dict) -> dict:
    cover = await deezer_service.search_track_cover(entry["title"], entry["artist"])
    return {**entry, "cover_url": cover}


async def get_hot_100(limit: int = 10) -> list[dict]:
    now = datetime.now(timezone.utc)
    if (
        _cache["data"] is not None
        and _cache["fetched_at"] is not None
        and now - _cache["fetched_at"] < _CACHE_TTL
    ):
        return _cache["data"][:limit]

    try:
        raw = await asyncio.to_thread(_fetch_chart_raw, limit)
        enriched = await asyncio.gather(*(_enrich_with_cover(e) for e in raw))
        results = list(enriched)
        if results:
            _cache["data"] = results
            _cache["fetched_at"] = now
        return results
    except Exception as exc:
        logger.warning("Billboard fetch failed: %s", exc)
        return _cache["data"][:limit] if _cache["data"] else []
