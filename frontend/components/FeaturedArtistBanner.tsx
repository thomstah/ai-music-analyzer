'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { BillboardSong, Song } from '@/types/song';
import { analyzeSong } from '@/lib/api';
import Spinner from '@/components/Spinner';

export default function FeaturedArtistBanner({ feature }: { feature: BillboardSong | null }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!feature) return null;

  async function handleListen() {
    if (loading) return;
    setLoading(true);
    setError(null);
    try {
      const song: Song = await analyzeSong(feature!.title, feature!.artist);
      sessionStorage.setItem(`song-${song.id}`, JSON.stringify(song));
      router.push(`/song/${song.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setLoading(false);
    }
  }

  return (
    <div className="relative overflow-hidden rounded-2xl mb-10 bg-gradient-to-br from-purple-900 via-neutral-900 to-neutral-950 p-8">
      <p className="text-xs font-bold text-purple-300 uppercase tracking-widest mb-2">
        Featured Today
      </p>
      <h2 className="text-4xl font-black text-white mb-1 leading-tight">{feature.artist}</h2>
      <p className="text-neutral-300 text-lg mb-4">
        <span className="text-neutral-500">Currently #1 with</span> {feature.title}
      </p>
      {error && <p className="text-red-400 text-xs mb-2">{error}</p>}
      <button
        onClick={handleListen}
        disabled={loading}
        className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white font-medium px-5 py-2 rounded-full transition-colors"
      >
        {loading ? <Spinner size="sm" /> : null}
        {loading ? 'Analyzing…' : 'Read the analysis →'}
      </button>
    </div>
  );
}
