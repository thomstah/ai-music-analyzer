import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import services.color as color_service


@pytest.mark.asyncio
async def test_extract_dominant_color_returns_none_for_empty_url():
    result = await color_service.extract_dominant_color("")
    assert result is None


@pytest.mark.asyncio
async def test_extract_dominant_color_returns_none_on_http_error():
    import httpx as _httpx
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=_httpx.RequestError("boom", request=MagicMock())
        )
        result = await color_service.extract_dominant_color("https://example.com/x.jpg")
    assert result is None


@pytest.mark.asyncio
async def test_extract_dominant_color_returns_hex_on_success():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.content = b"fake image bytes"

    with patch("httpx.AsyncClient") as mock_cls, \
         patch("services.color._extract_sync", return_value="#a34fbc"):
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await color_service.extract_dominant_color("https://example.com/art.jpg")
    assert result == "#a34fbc"


def test_pick_best_swatch_prefers_saturation():
    # First swatch is muted (grey-ish), second is highly saturated
    palette = [(100, 100, 100), (200, 30, 30), (60, 60, 60)]
    picked = color_service._pick_best_swatch(palette)
    assert picked == (200, 30, 30)


def test_pick_best_swatch_skips_near_black_and_white():
    # All swatches too dark; falls back to first
    palette = [(5, 5, 5), (240, 240, 240), (0, 0, 0)]
    picked = color_service._pick_best_swatch(palette)
    # No swatch survives the 0.1-0.9 lightness gate, so it returns the first (dominant)
    assert picked == (5, 5, 5)
