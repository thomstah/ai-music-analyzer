"""Extract a dominant color from an album cover URL.

Used to tint individual song pages with a color derived from their album art.
The extraction is best-effort — network or format failures return None and the
frontend falls back to the default page background.
"""
import asyncio
import colorsys
import logging
from io import BytesIO
from typing import Optional
import httpx
from colorthief import ColorThief

logger = logging.getLogger(__name__)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def _pick_best_swatch(palette: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    """From a palette, pick the swatch with the highest saturation. Falls back to
    the first (dominant) swatch when nothing is meaningfully saturated. Skips
    swatches that are near-black or near-white so the tint has visible color."""
    scored: list[tuple[float, tuple[int, int, int]]] = []
    for rgb in palette:
        r, g, b = (v / 255.0 for v in rgb)
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        # Skip extreme lightness values where a tint would be invisible
        if l < 0.1 or l > 0.9:
            continue
        scored.append((s, rgb))
    if not scored:
        return palette[0]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[0][1]


def _extract_sync(image_bytes: bytes) -> Optional[str]:
    try:
        buf = BytesIO(image_bytes)
        ct = ColorThief(buf)
        palette = ct.get_palette(color_count=5, quality=10)
    except Exception as exc:
        logger.warning("ColorThief failed: %s", exc)
        return None
    if not palette:
        return None
    best = _pick_best_swatch(palette)
    return _rgb_to_hex(best)


async def extract_dominant_color(image_url: str) -> Optional[str]:
    """Fetch the image and return the most saturated non-extreme palette swatch
    as a hex string like '#a34fbc'. Returns None on any failure."""
    if not image_url:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            image_bytes = response.content
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.warning("Cover art fetch failed for color extraction: %s", exc)
        return None
    # Colorthief is CPU-bound — run in a thread so we don't block the event loop.
    return await asyncio.to_thread(_extract_sync, image_bytes)
