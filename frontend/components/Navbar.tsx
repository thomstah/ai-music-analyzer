'use client';
import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { analyzeSong } from '@/lib/api';
import { Song } from '@/types/song';

export default function Navbar() {
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [artist, setArtist] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!title.trim() || !artist.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const song: Song = await analyzeSong(title.trim(), artist.trim());
      sessionStorage.setItem(`song-${song.id}`, JSON.stringify(song));
      router.push(`/song/${song.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  return (
    <nav className="bg-neutral-950 border-b border-neutral-800 px-6 py-3">
      <div className="max-w-6xl mx-auto flex items-center gap-6">
        <a href="/" className="text-purple-400 font-black text-lg tracking-widest shrink-0">
          LYRIQ
        </a>
        <form onSubmit={handleSearch} className="flex gap-2 flex-1 max-w-xl">
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Song title"
            className="flex-1 bg-neutral-800 text-white placeholder-neutral-500 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-purple-500"
          />
          <input
            value={artist}
            onChange={e => setArtist(e.target.value)}
            placeholder="Artist"
            className="w-36 bg-neutral-800 text-white placeholder-neutral-500 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-purple-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-sm px-4 py-1.5 rounded font-medium transition-colors"
          >
            {loading ? '...' : 'Search'}
          </button>
        </form>
        {error && <p className="text-red-400 text-xs shrink-0">{error}</p>}
      </div>
    </nav>
  );
}
