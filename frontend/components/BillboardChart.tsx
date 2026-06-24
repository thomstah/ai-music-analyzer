'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { BillboardSong, Song } from '@/types/song';
import { analyzeSong } from '@/lib/api';
import Spinner from '@/components/Spinner';

export default function BillboardChart({ songs }: { songs: BillboardSong[] }) {
  const router = useRouter();
  const [loadingKey, setLoadingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (songs.length === 0) {
    return (
      <p className="text-neutral-500 text-sm">
        Billboard chart unavailable. Search for a song above.
      </p>
    );
  }

  async function handleSelect(song: BillboardSong) {
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
    <div>
      {error && <p className="text-red-400 text-xs mb-3">{error}</p>}
      <ol className="space-y-2">
        {songs.map(song => {
          const key = `${song.title}-${song.artist}`;
          const isLoading = loadingKey === key;
          return (
            <li key={key}>
              <button
                onClick={() => handleSelect(song)}
                disabled={!!loadingKey}
                className="w-full flex items-center gap-4 bg-neutral-900 hover:bg-neutral-800 disabled:opacity-60 rounded-lg px-4 py-3 transition-colors text-left"
              >
                <span className="text-neutral-600 font-bold w-5 text-right text-sm shrink-0">
                  {song.rank}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-white font-semibold truncate">{song.title}</p>
                  <p className="text-neutral-400 text-sm truncate">{song.artist}</p>
                </div>
                <div className="w-4 h-4 shrink-0 flex items-center justify-center">
                  {isLoading && <Spinner size="sm" />}
                </div>
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
