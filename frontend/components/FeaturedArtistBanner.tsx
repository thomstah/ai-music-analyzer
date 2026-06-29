'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { BillboardSong, Song } from '@/types/song';
import { analyzeSong } from '@/lib/api';
import Spinner from '@/components/Spinner';

const AUTO_ROTATE_MS = 7000;

export default function FeaturedArtistBanner({ songs }: { songs: BillboardSong[] }) {
  const router = useRouter();
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);

  const featured = songs.slice(0, 5);

  useEffect(() => {
    if (paused || featured.length <= 1) return;
    const id = setInterval(() => {
      setIndex(i => (i + 1) % featured.length);
    }, AUTO_ROTATE_MS);
    return () => clearInterval(id);
  }, [paused, featured.length]);

  if (featured.length === 0) return null;

  const current = featured[index];

  async function handleListen() {
    if (loading) return;
    setLoading(true);
    setError(null);
    try {
      const song: Song = await analyzeSong(current.title, current.artist);
      sessionStorage.setItem(`song-${song.id}`, JSON.stringify(song));
      router.push(`/song/${song.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setLoading(false);
    }
  }

  function goPrev() {
    setIndex(i => (i - 1 + featured.length) % featured.length);
  }
  function goNext() {
    setIndex(i => (i + 1) % featured.length);
  }

  return (
    <div
      className="relative overflow-hidden rounded-2xl mb-6 bg-gradient-to-br from-purple-900 via-neutral-900 to-neutral-950 p-6"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-bold text-purple-300 uppercase tracking-widest">
          Featured Today
        </p>
        {featured.length > 1 && (
          <div className="flex gap-1">
            <button
              onClick={goPrev}
              aria-label="Previous featured song"
              className="w-7 h-7 flex items-center justify-center rounded-full bg-neutral-800/60 hover:bg-neutral-700 text-neutral-300 transition-colors"
            >
              ‹
            </button>
            <button
              onClick={goNext}
              aria-label="Next featured song"
              className="w-7 h-7 flex items-center justify-center rounded-full bg-neutral-800/60 hover:bg-neutral-700 text-neutral-300 transition-colors"
            >
              ›
            </button>
          </div>
        )}
      </div>

      <h2 className="text-3xl font-black text-white mb-1 leading-tight">{current.artist}</h2>
      <p className="text-neutral-300 mb-3">
        <span className="text-neutral-500">#{current.rank} with</span> {current.title}
      </p>

      {error && <p className="text-red-400 text-xs mb-2">{error}</p>}

      <div className="flex items-center gap-4 flex-wrap">
        <button
          onClick={handleListen}
          disabled={loading}
          className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-sm font-medium px-4 py-2 rounded-full transition-colors"
        >
          {loading && <Spinner size="sm" />}
          {loading ? 'Analyzing…' : 'Read the analysis →'}
        </button>

        {featured.length > 1 && (
          <div className="flex gap-1.5" role="tablist" aria-label="Featured song selector">
            {featured.map((_, i) => (
              <button
                key={i}
                onClick={() => setIndex(i)}
                aria-label={`Show featured song ${i + 1}`}
                aria-selected={i === index}
                role="tab"
                className={`w-2 h-2 rounded-full transition-colors ${
                  i === index ? 'bg-purple-400' : 'bg-neutral-700 hover:bg-neutral-600'
                }`}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
