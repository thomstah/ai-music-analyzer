from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AnalyzeRequest(BaseModel):
    title: str
    artist: str


class LyricBreakdown(BaseModel):
    lyric: str
    breakdown: str


class InterpretationContent(BaseModel):
    tldr: Optional[str] = None
    overall_meaning: str
    emotional_tone: str
    themes: list[str]
    key_lyric_breakdowns: list[LyricBreakdown]


class DiscourseExcerpt(BaseModel):
    source: str
    text: str
    url: Optional[str] = None
    metadata: dict = {}


class SongMetadata(BaseModel):
    album_art_url: Optional[str] = None
    album_name: Optional[str] = None
    release_year: Optional[str] = None
    producer: Optional[str] = None


class SongResponse(BaseModel):
    id: str
    title: str
    artist: str
    lyrics: str
    genius_id: Optional[int] = None
    created_at: Optional[datetime] = None
    interpretation: Optional[InterpretationContent] = None
    community_commentary: Optional[list[DiscourseExcerpt]] = None
    metadata: Optional[SongMetadata] = None


class Article(BaseModel):
    title: str
    description: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    source: str
    published_at: str
