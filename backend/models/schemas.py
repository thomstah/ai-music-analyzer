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
    overall_meaning: str
    emotional_tone: str
    themes: list[str]
    key_lyric_breakdowns: list[LyricBreakdown]

class SongResponse(BaseModel):
    id: str
    title: str
    artist: str
    lyrics: str
    genius_id: Optional[int] = None
    created_at: Optional[datetime] = None
    interpretation: Optional[InterpretationContent] = None
