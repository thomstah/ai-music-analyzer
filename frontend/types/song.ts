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
  artist_id: number | null;
  album_id: number | null;
  album_art_url: string | null;
  album_name: string | null;
  release_year: string | null;
  producer: string | null;
  musixmatch_url?: string | null;
  musixmatch_track_id?: number | null;
}

export interface AlbumTrack {
  genius_id: number | null;
  title: string;
  thumbnail: string | null;
}

export interface Album {
  id: string;
  genius_id: number | null;
  artist_id: number | null;
  title: string;
  artist: string;
  release_year: string | null;
  cover_art_url: string | null;
  producers: string[];
  tracklist: AlbumTrack[];
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

export interface ArtistTopSong {
  genius_id: number;
  title: string;
  thumbnail: string | null;
  artist_name: string;
}

export interface ArtistTopAlbum {
  album_id_deezer: number;
  title: string;
  cover_url: string | null;
  release_year: string | null;
}

export interface Artist {
  id: string;
  genius_id: number | null;
  deezer_id: number | null;
  name: string;
  alternate_names: string[];
  image_url: string | null;
  header_image_url: string | null;
  description_preview: string | null;
  description_full: string | null;
  top_songs: ArtistTopSong[];
  top_albums: ArtistTopAlbum[];
}
