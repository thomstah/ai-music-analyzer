"""In-memory token bucket rate limiter.

Single-process only. If the app is ever run with multiple uvicorn workers or
horizontally scaled, swap `_buckets` for a Redis-backed store — the `check`
signature can stay the same.
"""
import asyncio
import time

_buckets: dict[str, tuple[float, float]] = {}
_lock = asyncio.Lock()


async def check(key: str, capacity: int, refill_per_sec: float) -> bool:
    """Attempt to consume one token from `key`'s bucket. Returns True if allowed.

    - capacity: max tokens the bucket holds (also the initial fill).
    - refill_per_sec: tokens added per second (0.0 disables refill for the test path).
    """
    now = time.monotonic()
    async with _lock:
        tokens, last = _buckets.get(key, (float(capacity), now))
        if refill_per_sec > 0:
            tokens = min(float(capacity), tokens + (now - last) * refill_per_sec)
        if tokens < 1.0:
            _buckets[key] = (tokens, now)
            return False
        _buckets[key] = (tokens - 1.0, now)
        return True
