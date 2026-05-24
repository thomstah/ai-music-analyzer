import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from services.anthropic import generate_interpretation

VALID_INTERPRETATION = {
    "overall_meaning": "A song about existential dread.",
    "emotional_tone": "melancholic",
    "themes": ["mortality", "identity"],
    "key_lyric_breakdowns": [
        {"lyric": "Is this the real life?", "breakdown": "Questions the nature of reality."}
    ],
}


def _make_response(text: str) -> MagicMock:
    content = MagicMock()
    content.text = text
    response = MagicMock()
    response.content = [content]
    return response


@pytest.mark.asyncio
async def test_generate_interpretation_returns_parsed_json_and_model():
    with patch("services.anthropic.anthropic.AsyncAnthropic") as mock_cls:
        mock_cls.return_value.messages.create = AsyncMock(
            return_value=_make_response(json.dumps(VALID_INTERPRETATION))
        )
        result, model = await generate_interpretation("Bohemian Rhapsody", "Queen", "lyrics here")

    assert result["overall_meaning"] == VALID_INTERPRETATION["overall_meaning"]
    assert result["emotional_tone"] == "melancholic"
    assert "mortality" in result["themes"]
    assert model == "claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_generate_interpretation_retries_on_invalid_json():
    bad = _make_response("this is not json")
    good = _make_response(json.dumps(VALID_INTERPRETATION))

    with patch("services.anthropic.anthropic.AsyncAnthropic") as mock_cls:
        mock_cls.return_value.messages.create = AsyncMock(side_effect=[bad, good])
        result, _ = await generate_interpretation("Song", "Artist", "some lyrics")

    assert result["overall_meaning"] == VALID_INTERPRETATION["overall_meaning"]


@pytest.mark.asyncio
async def test_generate_interpretation_raises_502_after_two_failures():
    bad = _make_response("not json at all")

    with patch("services.anthropic.anthropic.AsyncAnthropic") as mock_cls:
        mock_cls.return_value.messages.create = AsyncMock(return_value=bad)
        with pytest.raises(HTTPException) as exc_info:
            await generate_interpretation("Song", "Artist", "lyrics")

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_generate_interpretation_retries_on_wrong_schema():
    wrong_schema = _make_response(json.dumps({"message": "I cannot analyze this"}))
    good = _make_response(json.dumps(VALID_INTERPRETATION))

    with patch("services.anthropic.anthropic.AsyncAnthropic") as mock_cls:
        mock_cls.return_value.messages.create = AsyncMock(side_effect=[wrong_schema, good])
        result, _ = await generate_interpretation("Song", "Artist", "lyrics")

    assert result["overall_meaning"] == VALID_INTERPRETATION["overall_meaning"]
