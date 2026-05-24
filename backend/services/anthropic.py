import json
import anthropic
from fastapi import HTTPException
from config import settings

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a music critic and literary analyst. Analyze the provided song lyrics and return a JSON object with exactly these fields:
- overall_meaning: 2-3 paragraphs interpreting the song's central message and narrative
- emotional_tone: a brief phrase describing the emotional character (e.g. "melancholic and introspective")
- themes: a list of 3-6 theme strings (e.g. ["loss", "memory", "identity"])
- key_lyric_breakdowns: a list of objects, each with "lyric" (a quoted fragment) and "breakdown" (explanation of its significance)

Return ONLY valid JSON. No markdown fences, no explanation outside the JSON object."""


async def generate_interpretation(title: str, artist: str, lyrics: str) -> tuple[dict, str]:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    user_message = f'Song: "{title}" by {artist}\n\nLyrics:\n{lyrics}'

    response = await client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_message}],
    )
    raw = response.content[0].text

    try:
        return json.loads(raw), MODEL
    except json.JSONDecodeError:
        pass

    retry = await client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": raw},
            {"role": "user", "content": "Your response was not valid JSON. Return ONLY the JSON object with no other text."},
        ],
    )
    try:
        return json.loads(retry.content[0].text), MODEL
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI interpretation service failed to return valid JSON")
