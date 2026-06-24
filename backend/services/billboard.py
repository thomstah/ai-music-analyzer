import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

_cache: dict = {"data": None, "fetched_at": None}
_CACHE_TTL = timedelta(hours=24)


def get_hot_100(limit: int = 10) -> list[dict]:
    now = datetime.now(timezone.utc)
    if (
        _cache["data"] is not None
        and _cache["fetched_at"] is not None
        and now - _cache["fetched_at"] < _CACHE_TTL
    ):
        return _cache["data"][:limit]

    try:
        import billboard  # type: ignore
        chart = billboard.ChartData("hot-100")
        results = [
            {"rank": i + 1, "title": entry.title, "artist": entry.artist}
            for i, entry in enumerate(chart[:limit])
        ]
        _cache["data"] = results
        _cache["fetched_at"] = now
        return results
    except Exception as exc:
        logger.warning("Billboard fetch failed: %s", exc)
        return _cache["data"][:limit] if _cache["data"] else []
