import { Song, SearchResults, BillboardSong, Article, TrendingTheme, Album, Artist, ThemeSongResult, DeezerAlbum, SimilarSong } from '@/types/song';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export class BudgetExhaustedError extends Error {
  resetsOn: string | null;
  constructor(message: string, resetsOn: string | null) {
    super(message);
    this.name = 'BudgetExhaustedError';
    this.resetsOn = resetsOn;
  }
}

export class RateLimitedError extends Error {
  retryAfterSeconds: number;
  constructor(message: string, retryAfterSeconds: number) {
    super(message);
    this.name = 'RateLimitedError';
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

async function throwTypedIfRateLimited(res: Response): Promise<void> {
  if (res.status !== 429) return;
  const retry = parseInt(res.headers.get('Retry-After') ?? '60', 10);
  const body = await res.json().catch(() => ({})) as { detail?: string };
  throw new RateLimitedError(body.detail ?? 'Slow down for a moment.', retry);
}

export async function analyzeSong(title: string, artist: string): Promise<Song> {
  const res = await fetch(`${BASE_URL}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, artist }),
  });
  await throwTypedIfRateLimited(res);
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function deepAnalyzeSong(songId: string): Promise<Song> {
  const res = await fetch(`${BASE_URL}/songs/${songId}/deep-analyze`, { method: 'POST' });
  await throwTypedIfRateLimited(res);
  if (res.status === 402) {
    const body = await res.json().catch(() => ({})) as { detail?: string; resets_on?: string };
    throw new BudgetExhaustedError(
      body.detail ?? "Lyriq's analysis budget is out for the month.",
      body.resets_on ?? null,
    );
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function getSongById(id: string): Promise<Song | null> {
  const res = await fetch(`${BASE_URL}/song/${id}`, { cache: 'no-store' });
  if (!res.ok) return null;
  return res.json();
}

export async function searchSongs(q: string): Promise<SearchResults> {
  const empty: SearchResults = { songs: [], lyrics: [], artists: [], albums: [] };
  const res = await fetch(
    `${BASE_URL}/songs/search?q=${encodeURIComponent(q)}`,
    { cache: 'no-store' },
  );
  if (!res.ok) return empty;
  return res.json();
}

export async function getBillboard(limit = 10): Promise<BillboardSong[]> {
  const res = await fetch(`${BASE_URL}/songs/billboard?limit=${limit}`, {
    cache: 'no-store',
  });
  if (!res.ok) return [];
  return res.json();
}

export async function getMusicNews(limit = 8): Promise<Article[]> {
  const res = await fetch(`${BASE_URL}/news?limit=${limit}`, { cache: 'no-store' });
  if (!res.ok) return [];
  return res.json();
}

export async function getTrendingThemes(limit = 5): Promise<TrendingTheme[]> {
  const res = await fetch(`${BASE_URL}/trending/themes?limit=${limit}`, { cache: 'no-store' });
  if (!res.ok) return [];
  return res.json();
}

export async function getSongsByTheme(theme: string, limit = 20): Promise<ThemeSongResult[]> {
  const res = await fetch(
    `${BASE_URL}/songs/by-theme?theme=${encodeURIComponent(theme)}&limit=${limit}`,
    { cache: 'no-store' },
  );
  if (!res.ok) return [];
  return res.json();
}

export async function getAlbumById(albumId: string | number): Promise<Album | null> {
  const res = await fetch(`${BASE_URL}/album/${albumId}`, { cache: 'no-store' });
  if (!res.ok) return null;
  return res.json();
}

export async function getDeezerAlbum(deezerId: string | number): Promise<DeezerAlbum | null> {
  const res = await fetch(`${BASE_URL}/album/deezer/${deezerId}`, { cache: 'no-store' });
  if (!res.ok) return null;
  return res.json();
}

export async function getArtistById(artistId: string | number): Promise<Artist | null> {
  const res = await fetch(`${BASE_URL}/artist/${artistId}`, { cache: 'no-store' });
  if (!res.ok) return null;
  return res.json();
}

export async function lookupArtistByName(name: string): Promise<number | null> {
  const res = await fetch(`${BASE_URL}/artist/by-name/${encodeURIComponent(name)}`, { cache: 'no-store' });
  if (!res.ok) return null;
  const data = await res.json() as { genius_id: number };
  return data.genius_id;
}

export async function getSimilarSongs(id: string, limit = 3): Promise<SimilarSong[]> {
  const res = await fetch(`${BASE_URL}/song/${id}/similar?limit=${limit}`, { cache: 'no-store' });
  if (!res.ok) return [];
  return res.json();
}

export interface StatusResponse {
  degraded: boolean;
  claude_budget: { remaining_usd: number; resets_on: string };
}

export async function getStatus(): Promise<StatusResponse | null> {
  try {
    const res = await fetch(`${BASE_URL}/status`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
