export interface LyricBreakdown {
  lyric: string;
  breakdown: string;
}

export interface DiscourseExcerpt {
  source: string;
  text: string;
  url: string | null;
  metadata: Record<string, string>;
}

export interface Interpretation {
  tldr?: string;
  overall_meaning: string;
  emotional_tone: string;
  themes: string[];
  key_lyric_breakdowns: LyricBreakdown[];
}

export interface SongMetadata {
  album_art_url: string | null;
  album_name: string | null;
  release_year: string | null;
  producer: string | null;
}

export interface Song {
  id: string;
  title: string;
  artist: string;
  lyrics: string;
  genius_id: number | null;
  created_at: string;
  interpretation: Interpretation | null;
  community_commentary: DiscourseExcerpt[] | null;
  metadata?: SongMetadata | null;
}

export interface SearchResult {
  title: string;
  artist: string;
  genius_id: number;
  thumbnail: string | null;
}

export interface ArtistResult {
  name: string;
  artist_id: number;
  thumbnail: string | null;
}

export interface AlbumSearchResult {
  album_id: number;
  name: string;
  artist: string;
  thumbnail: string | null;
}

export interface SearchResults {
  songs: SearchResult[];
  lyrics: SearchResult[];
  artists: ArtistResult[];
  albums: AlbumSearchResult[];
}

export interface BillboardSong {
  rank: number;
  title: string;
  artist: string;
}

export interface Article {
  title: string;
  description: string | null;
  url: string;
  image_url: string | null;
  source: string;
  published_at: string;
}

export interface TrendingTheme {
  theme: string;
  count: number;
}
