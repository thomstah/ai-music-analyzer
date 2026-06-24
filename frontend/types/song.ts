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

export interface Song {
  id: string;
  title: string;
  artist: string;
  lyrics: string;
  genius_id: number | null;
  created_at: string;
  interpretation: Interpretation | null;
  community_commentary: DiscourseExcerpt[] | null;
}

export interface TrendingSong {
  id: string;
  title: string;
  artist: string;
  request_count: number;
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

export interface SearchResults {
  songs: SearchResult[];
  lyrics: SearchResult[];
  artists: ArtistResult[];
}
