'use client';
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { BillboardSong, Song } from '@/types/song';
import { analyzeSong } from '@/lib/api';
import Spinner from '@/components/Spinner';

const AUTO_ROTATE_MS = 4500;

export default function FeaturedArtistBanner({ songs }: { songs: BillboardSong[] }) {
  const router = useRouter();
  const trackRef = useRef<HTMLDivElement>(null);
  const [loadingKey, setLoadingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);

  const featured = songs.slice(0, 10);

  function getStepWidth(): number {
    const track = trackRef.current;
    if (!track || track.children.length < 2) return 0;
    const first = track.children[0] as HTMLElement;
    const second = track.children[1] as HTMLElement;
    return second.offsetLeft - first.offsetLeft;
  }

  function scrollByStep(direction: -1 | 1) {
    const track = trackRef.current;
    if (!track) return;
    const step = getStepWidth();
    if (step === 0) return;
    track.scrollBy({ left: direction * step, behavior: 'smooth' });
  }

  // Auto-advance, wrap around at the end
  useEffect(() => {
    if (paused || featured.length <= 1) return;
    const id = setInterval(() => {
      const track = trackRef.current;
      if (!track) return;
      const step = getStepWidth();
      if (step === 0) return;
      const atEnd = track.scrollLeft + track.clientWidth >= track.scrollWidth - 4;
      if (atEnd) {
        track.scrollTo({ left: 0, behavior: 'smooth' });
      } else {
        track.scrollBy({ left: step, behavior: 'smooth' });
      }
    }, AUTO_ROTATE_MS);
    return () => clearInterval(id);
  }, [paused, featured.length]);

  if (featured.length === 0) return null;

  async function handleListen(song: BillboardSong) {
    const key = `${song.title}-${song.artist}`;
    if (loadingKey) return;
    setLoadingKey(key);
    setError(null);
    try {
      const result: Song = await analyzeSong(song.title, song.artist);
      sessionStorage.setItem(`song-${result.id}`, JSON.stringify(result));
      router.push(`/song/${result.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setLoadingKey(null);
    }
  }

  return (
    <div
      className="relative mb-6"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-bold text-purple-300 uppercase tracking-widest">
          Featured Today
        </p>
        {featured.length > 1 && (
          <div className="flex gap-1">
            <button
              onClick={() => scrollByStep(-1)}
              aria-label="Previous featured"
              className="w-7 h-7 flex items-center justify-center rounded-full bg-neutral-800 hover:bg-neutral-700 text-neutral-300 transition-colors text-lg leading-none"
            >
              ‹
            </button>
            <button
              onClick={() => scrollByStep(1)}
              aria-label="Next featured"
              className="w-7 h-7 flex items-center justify-center rounded-full bg-neutral-800 hover:bg-neutral-700 text-neutral-300 transition-colors text-lg leading-none"
            >
              ›
            </button>
          </div>
        )}
      </div>

      <div
        ref={trackRef}
        className="flex gap-3 overflow-x-auto snap-x snap-mandatory scroll-smooth no-scrollbar"
      >
        {featured.map(song => {
          const key = `${song.title}-${song.artist}`;
          const isLoading = loadingKey === key;
          return (
            <div
              key={key}
              className="snap-start shrink-0 basis-full sm:basis-1/2 lg:basis-1/3"
            >
              <div className="bg-gradient-to-br from-purple-900 via-neutral-900 to-neutral-950 rounded-2xl p-5 h-full flex flex-col justify-between min-h-[160px]">
                <div className="min-w-0">
                  <p className="text-xs font-bold text-purple-300 uppercase tracking-widest mb-2">
                    #{song.rank} on Billboard
                  </p>
                  <h3 className="text-xl font-black text-white leading-tight mb-1 truncate">
                    {song.title}
                  </h3>
                  <p className="text-neutral-400 text-sm truncate">{song.artist}</p>
                </div>
                <button
                  onClick={() => handleListen(song)}
                  disabled={!!loadingKey}
                  className="mt-3 inline-flex items-center gap-2 text-purple-300 hover:text-purple-200 text-sm font-medium transition-colors disabled:opacity-60 self-start"
                >
                  {isLoading && <Spinner size="sm" />}
                  {isLoading ? 'Analyzing…' : 'Read the analysis →'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
    </div>
  );
}
