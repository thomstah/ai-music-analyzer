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
    artist_id: Optional[int] = None
    album_id: Optional[int] = None
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


class TrendingTheme(BaseModel):
    theme: str
    count: int


class AlbumSearchResult(BaseModel):
    album_id: int
    name: str
    artist: str
    thumbnail: Optional[str] = None


class AlbumTrack(BaseModel):
    genius_id: Optional[int] = None
    title: str
    thumbnail: Optional[str] = None


class AlbumResponse(BaseModel):
    id: str
    genius_id: Optional[int] = None
    artist_id: Optional[int] = None
    title: str
    artist: str
    release_year: Optional[str] = None
    cover_art_url: Optional[str] = None
    producers: list[str] = []
    tracklist: list[AlbumTrack] = []


class ArtistTopSong(BaseModel):
    genius_id: int
    title: str
    thumbnail: Optional[str] = None
    artist_name: str = ""


class ArtistTopAlbum(BaseModel):
    album_id_deezer: int
    title: str
    cover_url: Optional[str] = None
    release_year: Optional[str] = None


class ArtistResponse(BaseModel):
    id: str
    genius_id: Optional[int] = None
    deezer_id: Optional[int] = None
    name: str
    alternate_names: list[str] = []
    image_url: Optional[str] = None
    header_image_url: Optional[str] = None
    description_preview: Optional[str] = None
    top_songs: list[ArtistTopSong] = []
    top_albums: list[ArtistTopAlbum] = []
