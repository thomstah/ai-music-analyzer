import anthropic
from typing import Optional
from fastapi import HTTPException
from config import settings
import services.claude_budget as claude_budget

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 4000

SYSTEM_PROMPT = """You are a music critic and literary analyst. Analyze the provided song lyrics and call the submit_interpretation tool with your analysis.

For key_lyric_breakdowns: quote 5-10 consecutive lyric lines VERBATIM from the source for each entry, separated by newlines. The breakdown must analyze those specific quoted lines so the card reads as a complete piece of criticism on its own. Never write "the bridge" or "this line" — always include the actual quoted lines so the reader can follow your analysis without scrolling to lyrics."""

INTERPRETATION_TOOL = {
    "name": "submit_interpretation",
    "description": "Submit your structured interpretation of the song.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tldr": {
                "type": "string",
                "description": "1-2 sentences, under 200 characters — the most essential thing to understand about the song. Plain language, no jargon.",
            },
            "overall_meaning": {
                "type": "string",
                "description": "2-3 paragraphs interpreting the song's central message and narrative.",
            },
            "emotional_tone": {
                "type": "string",
                "description": "A brief phrase describing the emotional character (e.g. 'melancholic and introspective').",
            },
            "themes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-6 theme strings (e.g. ['loss', 'memory', 'identity']).",
            },
            "key_lyric_breakdowns": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "lyric": {
                            "type": "string",
                            "description": "5-10 consecutive lyric lines quoted VERBATIM from the source, separated by newlines.",
                        },
                        "breakdown": {
                            "type": "string",
                            "description": "2-4 sentences of commentary on the specific quoted lines — imagery, meaning, technique, or context.",
                        },
                    },
                    "required": ["lyric", "breakdown"],
                },
                "description": "4-6 objects covering the most meaningful moments in the song.",
            },
        },
        "required": ["tldr", "overall_meaning", "emotional_tone", "themes", "key_lyric_breakdowns"],
    },
}


def _build_user_message(title: str, artist: str, lyrics: str, discourse: Optional[list[dict]]) -> str:
    message = f'Song: "{title}" by {artist}\n\nLyrics:\n{lyrics}'
    if not discourse:
        return message

    lines = []
    for exc in discourse:
        source = exc.get("source", "")
        text = exc.get("text", "")
        if not text:
            continue
        metadata = exc.get("metadata", {})
        if source == "reddit":
            subreddit = metadata.get("subreddit", "")
            lines.append(f'[reddit] {subreddit}: "{text}"')
        elif source == "genius":
            fragment = metadata.get("lyric_fragment", "")
            lines.append(f'[genius] "{fragment}" → "{text}"')
        else:
            lines.append(f'[{source}] "{text}"')

    if lines:
        message += "\n\nCommunity Commentary (Reddit threads and Genius annotations — use these to inform your interpretation):\n"
        message += "\n".join(lines)
    return message


def _extract_tool_input(response) -> Optional[dict]:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "submit_interpretation":
            return block.input
    return None


async def generate_interpretation(
    title: str,
    artist: str,
    lyrics: str,
    discourse: Optional[list[dict]] = None,
) -> tuple[dict, str]:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    user_message = _build_user_message(title, artist, lyrics, discourse)

    response = await client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        tools=[INTERPRETATION_TOOL],
        tool_choice={"type": "tool", "name": "submit_interpretation"},
        messages=[{"role": "user", "content": user_message}],
    )
    claude_budget.record_usage(response.usage.input_tokens, response.usage.output_tokens)

    parsed = _extract_tool_input(response)
    if parsed is not None:
        return parsed, MODEL

    raise HTTPException(status_code=502, detail="AI interpretation service did not return a structured response")
