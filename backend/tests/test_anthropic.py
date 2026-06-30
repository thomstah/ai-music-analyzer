import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from services.anthropic import generate_interpretation, REQUIRED_KEYS

VALID_INTERPRETATION = {
    "tldr": "A song about existential dread.",
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
    response.usage = MagicMock(input_tokens=100, output_tokens=500)
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
    assert model == "claude-haiku-4-5-20251001"


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


@pytest.mark.asyncio
async def test_generate_interpretation_includes_discourse_in_user_message():
    discourse = [
        {
            "source": "reddit",
            "text": "This track is about Drake processing grief after losing a close friend.",
            "url": "https://reddit.com/r/hiphopheads/comments/xyz",
            "metadata": {"subreddit": "r/hiphopheads"},
        },
        {
            "source": "genius",
            "text": "A reference to the Houston lean culture Drake adopted.",
            "url": None,
            "metadata": {"lyric_fragment": "I sipped lean"},
        },
    ]

    captured = []

    async def capture(**kwargs):
        captured.append(kwargs["messages"][0]["content"])
        return _make_response(json.dumps(VALID_INTERPRETATION))

    with patch("services.anthropic.anthropic.AsyncAnthropic") as mock_cls:
        mock_cls.return_value.messages.create = capture
        await generate_interpretation("Passionfruit", "Drake", "lyrics here", discourse=discourse)

    assert len(captured) == 1
    user_content = captured[0]
    assert "Community Commentary" in user_content
    assert "r/hiphopheads" in user_content
    assert "I sipped lean" in user_content


@pytest.mark.asyncio
async def test_generate_interpretation_includes_tldr():
    valid_response = json.dumps({
        "tldr": "A song about betrayal and moving on.",
        "overall_meaning": "This song explores the themes of...",
        "emotional_tone": "melancholic",
        "themes": ["loss", "betrayal"],
        "key_lyric_breakdowns": [{"lyric": "test line", "breakdown": "means this"}],
    })
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=valid_response)]

    with patch("services.anthropic.anthropic.AsyncAnthropic") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value = mock_instance
        mock_instance.messages.create = AsyncMock(return_value=mock_response)
        result, model = await generate_interpretation("Song", "Artist", "lyrics here")

    assert "tldr" in result
    assert result["tldr"] == "A song about betrayal and moving on."
    assert "tldr" in REQUIRED_KEYS
