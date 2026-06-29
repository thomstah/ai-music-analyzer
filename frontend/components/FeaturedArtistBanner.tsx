'use client';
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { BillboardSong, Song } from '@/types/song';
import { analyzeSong } from '@/lib/api';
import Spinner from '@/components/Spinner';
import MarqueeText from '@/components/MarqueeText';

const AUTO_ROTATE_MS = 10000;

export default function FeaturedArtistBanner({ songs }: { songs: BillboardSong[] }) {
  const router = useRouter();
  const trackRef = useRef<HTMLDivElement>(null);
  const [loadingKey, setLoadingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const [cycleCount, setCycleCount] = useState(0);

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
    setCycleCount(c => c + 1);
  }

  // Auto-advance, wrap around at the end. Track cycleCount so the progress bar resets.
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
      setCycleCount(c => c + 1);
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
              className="snap-start shrink-0 min-w-0 basis-full sm:basis-[calc((100%-0.75rem)/2)] lg:basis-[calc((100%-1.5rem)/3)]"
            >
              <div className="bg-gradient-to-br from-purple-900 via-neutral-900 to-neutral-950 rounded-2xl p-4 h-full flex gap-3 items-center">
                {song.cover_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={song.cover_url}
                    alt=""
                    width={80}
                    height={80}
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                    className="w-20 h-20 rounded-lg shadow-lg shrink-0 object-cover"
                  />
                ) : (
                  <div className="w-20 h-20 rounded-lg bg-neutral-800 shrink-0 flex items-center justify-center">
                    <span className="text-neutral-600 text-xs font-bold">#{song.rank}</span>
                  </div>
                )}
                <div className="min-w-0 flex-1 flex flex-col justify-center">
                  <p className="text-xs font-bold text-purple-300 uppercase tracking-widest mb-1">
                    #{song.rank} on Billboard
                  </p>
                  <MarqueeText
                    text={song.title}
                    className="text-base font-black text-white leading-tight"
                  />
                  <MarqueeText
                    text={song.artist}
                    className="text-neutral-400 text-sm mt-0.5"
                  />
                  <button
                    onClick={() => handleListen(song)}
                    disabled={!!loadingKey}
                    className="mt-2 inline-flex items-center gap-1.5 text-purple-300 hover:text-purple-200 text-xs font-medium transition-colors disabled:opacity-60 self-start"
                  >
                    {isLoading && <Spinner size="sm" />}
                    {isLoading ? 'Analyzing…' : 'Read the analysis →'}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Auto-cycle progress bar. The `key` resets the CSS animation each tick. */}
      {featured.length > 1 && (
        <div className="h-0.5 bg-neutral-800/60 rounded-full overflow-hidden mt-3">
          <div
            key={cycleCount}
            className="h-full bg-purple-500/70 animate-progress"
            style={{ animationPlayState: paused ? 'paused' : 'running' }}
          />
        </div>
      )}

      {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
    </div>
  );
}
