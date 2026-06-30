import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from services.anthropic import generate_interpretation

VALID_INTERPRETATION = {
    "tldr": "A song about existential dread.",
    "overall_meaning": "A song about existential dread.",
    "emotional_tone": "melancholic",
    "themes": ["mortality", "identity"],
    "key_lyric_breakdowns": [
        {
            "lyric": "Is this the real life?\nIs this just fantasy?",
            "breakdown": "Questions the nature of reality, framing the song's central tension.",
        }
    ],
}


def _make_tool_response(tool_input: dict) -> MagicMock:
    """Build a mock Anthropic response containing a single tool_use block."""
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "submit_interpretation"
    tool_block.input = tool_input
    response = MagicMock()
    response.content = [tool_block]
    response.usage = MagicMock(input_tokens=100, output_tokens=500)
    return response


def _make_text_only_response(text: str) -> MagicMock:
    """A response with no tool_use block — simulates Claude refusing the tool."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text
    response = MagicMock()
    response.content = [text_block]
    response.usage = MagicMock(input_tokens=100, output_tokens=500)
    return response


@pytest.mark.asyncio
async def test_generate_interpretation_returns_parsed_json_and_model():
    with patch("services.anthropic.anthropic.AsyncAnthropic") as mock_cls:
        mock_cls.return_value.messages.create = AsyncMock(
            return_value=_make_tool_response(VALID_INTERPRETATION)
        )
        result, model = await generate_interpretation("Bohemian Rhapsody", "Queen", "lyrics here")

    assert result["overall_meaning"] == VALID_INTERPRETATION["overall_meaning"]
    assert result["emotional_tone"] == "melancholic"
    assert "mortality" in result["themes"]
    assert model == "claude-haiku-4-5-20251001"


@pytest.mark.asyncio
async def test_generate_interpretation_raises_502_when_no_tool_use_block():
    """If Claude returns text instead of calling the tool, raise a clean 502."""
    with patch("services.anthropic.anthropic.AsyncAnthropic") as mock_cls:
        mock_cls.return_value.messages.create = AsyncMock(
            return_value=_make_text_only_response("I cannot analyze this song.")
        )
        with pytest.raises(HTTPException) as exc_info:
            await generate_interpretation("Song", "Artist", "lyrics")

    assert exc_info.value.status_code == 502


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
        return _make_tool_response(VALID_INTERPRETATION)

    with patch("services.anthropic.anthropic.AsyncAnthropic") as mock_cls:
        mock_cls.return_value.messages.create = capture
        await generate_interpretation("Passionfruit", "Drake", "lyrics here", discourse=discourse)

    assert len(captured) == 1
    user_content = captured[0]
    assert "Community Commentary" in user_content
    assert "r/hiphopheads" in user_content
    assert "I sipped lean" in user_content


@pytest.mark.asyncio
async def test_generate_interpretation_uses_tool_choice_to_force_schema():
    """Verify the API call forces the submit_interpretation tool."""
    captured_kwargs = {}

    async def capture(**kwargs):
        captured_kwargs.update(kwargs)
        return _make_tool_response(VALID_INTERPRETATION)

    with patch("services.anthropic.anthropic.AsyncAnthropic") as mock_cls:
        mock_cls.return_value.messages.create = capture
        await generate_interpretation("Song", "Artist", "lyrics")

    assert captured_kwargs["tool_choice"] == {"type": "tool", "name": "submit_interpretation"}
    assert len(captured_kwargs["tools"]) == 1
    assert captured_kwargs["tools"][0]["name"] == "submit_interpretation"
