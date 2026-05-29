import logging
import httpx
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)

GENIUS_API_BASE = "https://api.genius.com"
REDDIT_HEADERS = {"User-Agent": "ai-music-analyzer/1.0"}
MAX_REDDIT_EXCERPTS = 10
MIN_COMMENT_LENGTH = 50
MAX_THREADS = 5
MAX_COMMENTS_PER_THREAD = 3
MAX_GENIUS_ANNOTATIONS = 5


async def fetch_discourse(genius_id: Optional[int], title: str, artist: str) -> list[dict]:
    excerpts = []
    excerpts.extend(await _fetch_reddit(title, artist))
    if genius_id is not None:
        excerpts.extend(await _fetch_genius_annotations(genius_id))
    return excerpts


async def _fetch_reddit(title: str, artist: str) -> list[dict]:
    excerpts = []
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=REDDIT_HEADERS) as client:
            search_resp = await client.get(
                "https://www.reddit.com/search.json",
                params={"q": f'"{title}" "{artist}"', "sort": "top", "t": "all", "limit": MAX_THREADS, "type": "link"},
            )
            search_resp.raise_for_status()
            threads = search_resp.json()["data"]["children"]

            for thread in threads:
                if len(excerpts) >= MAX_REDDIT_EXCERPTS:
                    break
                td = thread["data"]
                subreddit = td.get("subreddit_name_prefixed", "r/unknown")
                post_id = td.get("id")
                thread_subreddit = td.get("subreddit")
                if not post_id or not thread_subreddit:
                    continue
                thread_url = f"https://reddit.com{td.get('permalink', '')}"

                comments_resp = await client.get(
                    f"https://www.reddit.com/r/{thread_subreddit}/comments/{post_id}.json",
                    params={"sort": "top", "limit": MAX_COMMENTS_PER_THREAD + 3},
                )
                comments_resp.raise_for_status()
                comments_data = comments_resp.json()

                if len(comments_data) < 2:
                    continue

                count = 0
                for comment in comments_data[1]["data"]["children"]:
                    if count >= MAX_COMMENTS_PER_THREAD or len(excerpts) >= MAX_REDDIT_EXCERPTS:
                        break
                    body = comment["data"].get("body", "")
                    if len(body) >= MIN_COMMENT_LENGTH and body not in ("[deleted]", "[removed]"):
                        excerpts.append({
                            "source": "reddit",
                            "text": body,
                            "url": thread_url,
                            "metadata": {"subreddit": subreddit},
                        })
                        count += 1
    except Exception as exc:
        logger.warning("Reddit scraping failed: %s", exc)
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
        logger.warning("Genius annotations fetch failed: %s", exc)
    return excerpts
