import logging
import httpx
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)

GENIUS_API_BASE = "https://api.genius.com"
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
MAX_YOUTUBE_COMMENTS = 10
MIN_COMMENT_LENGTH = 50
MAX_GENIUS_ANNOTATIONS = 5


async def fetch_discourse(genius_id: Optional[int], title: str, artist: str) -> list[dict]:
    excerpts = []
    if genius_id is not None:
        excerpts.extend(await _fetch_genius_annotations(genius_id))
    excerpts.extend(await _fetch_youtube_comments(title, artist))
    return excerpts


async def _fetch_youtube_comments(title: str, artist: str) -> list[dict]:
    excerpts = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            search_resp = await client.get(
                f"{YOUTUBE_API_BASE}/search",
                params={
                    "part": "snippet",
                    "q": f"{title} {artist}",
                    "type": "video",
                    "videoCategoryId": "10",
                    "maxResults": 3,
                    "key": settings.youtube_api_key,
                },
            )
            search_resp.raise_for_status()
            items = search_resp.json().get("items", [])
            if not items:
                return excerpts

            video_id = items[0]["id"]["videoId"]
            video_title = items[0]["snippet"]["title"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            comments_resp = await client.get(
                f"{YOUTUBE_API_BASE}/commentThreads",
                params={
                    "part": "snippet",
                    "videoId": video_id,
                    "order": "relevance",
                    "maxResults": MAX_YOUTUBE_COMMENTS + 5,
                    "textFormat": "plainText",
                    "key": settings.youtube_api_key,
                },
            )
            comments_resp.raise_for_status()
            threads = comments_resp.json().get("items", [])

            for thread in threads:
                if len(excerpts) >= MAX_YOUTUBE_COMMENTS:
                    break
                comment = thread["snippet"]["topLevelComment"]["snippet"]
                text = comment.get("textDisplay", "")
                if len(text) >= MIN_COMMENT_LENGTH:
                    excerpts.append({
                        "source": "youtube",
                        "text": text,
                        "url": video_url,
                        "metadata": {"video_title": video_title},
                    })
    except Exception as exc:
        logger.warning("YouTube comments fetch failed: %s", exc, exc_info=True)
    return excerpts


async def _fetch_genius_annotations(genius_id: int) -> list[dict]:
    excerpts = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{GENIUS_API_BASE}/referents",
                params={"song_id": genius_id, "text_format": "plain"},
                headers={"Authorization": f"Bearer {settings.genius_access_token}"},
            )
            resp.raise_for_status()
            referents = resp.json()["response"]["referents"]

            def annotation_length(ref):
                anns = ref.get("annotations", [])
                return len(anns[0].get("body", {}).get("plain", "")) if anns else 0

            for ref in sorted(referents, key=annotation_length, reverse=True)[:MAX_GENIUS_ANNOTATIONS]:
                anns = ref.get("annotations", [])
                if not anns:
                    continue
                text = anns[0].get("body", {}).get("plain", "")
                if text:
                    excerpts.append({
                        "source": "genius",
                        "text": text,
                        "url": None,
                        "metadata": {"lyric_fragment": ref.get("fragment", "")},
                    })
    except Exception as exc:
        logger.warning("Genius annotations fetch failed: %s", exc, exc_info=True)
    return excerpts
