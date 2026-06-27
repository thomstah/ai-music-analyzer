'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { AlbumTrack, Song } from '@/types/song';
import { analyzeSong } from '@/lib/api';
import Spinner from '@/components/Spinner';

export default function Tracklist({
  tracks,
  artist,
}: {
  tracks: AlbumTrack[];
  artist: string;
}) {
  const router = useRouter();
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (tracks.length === 0) {
    return <p className="text-neutral-500 text-sm">No tracks listed.</p>;
  }

  async function handleSelect(track: AlbumTrack) {
    if (!track.genius_id || loadingId !== null) return;
    setLoadingId(track.genius_id);
    setError(null);
    try {
      const song: Song = await analyzeSong(track.title, artist);
      sessionStorage.setItem(`song-${song.id}`, JSON.stringify(song));
      router.push(`/song/${song.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setLoadingId(null);
    }
  }

  return (
    <div>
      {error && <p className="text-red-400 text-xs mb-3">{error}</p>}
      <ol className="space-y-1">
        {tracks.map((track, i) => (
          <li key={track.genius_id ?? i}>
            <button
              onClick={() => handleSelect(track)}
              disabled={!!loadingId}
              className="w-full flex items-center gap-4 hover:bg-neutral-800 disabled:opacity-60 rounded px-3 py-2 transition-colors text-left"
            >
              <span className="text-neutral-600 font-medium w-6 text-right text-sm shrink-0">
                {i + 1}
              </span>
              <span className="text-white text-sm flex-1 min-w-0 truncate">{track.title}</span>
              <div className="w-4 h-4 shrink-0 flex items-center justify-center">
                {loadingId === track.genius_id && <Spinner size="sm" />}
              </div>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
