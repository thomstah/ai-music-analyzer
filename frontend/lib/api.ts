import { Song, TrendingSong, SearchResult } from '@/types/song';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function analyzeSong(title: string, artist: string): Promise<Song> {
  const res = await fetch(`${BASE_URL}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, artist }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function getTrending(limit = 10): Promise<TrendingSong[]> {
  const res = await fetch(`${BASE_URL}/songs/trending?limit=${limit}`, {
    cache: 'no-store',
  });
  if (!res.ok) return [];
  return res.json();
}

export async function getSongById(id: string): Promise<Song | null> {
  const res = await fetch(`${BASE_URL}/song/${id}`, { cache: 'no-store' });
  if (!res.ok) return null;
  return res.json();
}

export async function searchSongs(q: string): Promise<SearchResult[]> {
  const res = await fetch(
    `${BASE_URL}/songs/search?q=${encodeURIComponent(q)}`,
    { cache: 'no-store' },
  );
  if (!res.ok) return [];
  return res.json();
}
