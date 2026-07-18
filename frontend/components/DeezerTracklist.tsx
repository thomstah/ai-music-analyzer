'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { DeezerAlbumTrack, Song } from '@/types/song';
import { analyzeSong } from '@/lib/api';
import Spinner from '@/components/Spinner';
import { useAnalyzeProgress } from '@/hooks/useAnalyzeProgress';

function TrackRow({
  track,
  index,
  loading,
  disabled,
  onClick,
}: {
  track: DeezerAlbumTrack;
  index: number;
  loading: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  const message = useAnalyzeProgress(loading);
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="w-full flex items-center gap-4 rounded px-3 py-2 hover:bg-neutral-800 disabled:opacity-60 transition-colors text-left"
    >
      <span className="text-neutral-600 font-medium w-6 text-right text-sm shrink-0">
        {index + 1}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-white text-sm truncate">{track.title}</p>
        {loading && (
          <p className="text-purple-300 text-xs truncate">{message}</p>
        )}
      </div>
      <div className="w-4 h-4 shrink-0 flex items-center justify-center">
        {loading && <Spinner size="sm" />}
      </div>
    </button>
  );
}

export default function DeezerTracklist({
  tracks,
  artist,
}: {
  tracks: DeezerAlbumTrack[];
  artist: string;
}) {
  const router = useRouter();
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (tracks.length === 0) {
    return <p className="text-neutral-500 text-sm">No tracks listed.</p>;
  }

  async function handleSelect(track: DeezerAlbumTrack) {
    if (loadingId !== null) return;
    setLoadingId(track.deezer_id);
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
          <li key={track.deezer_id}>
            <TrackRow
              track={track}
              index={i}
              loading={loadingId === track.deezer_id}
              disabled={loadingId !== null}
              onClick={() => handleSelect(track)}
            />
          </li>
        ))}
      </ol>
    </div>
  );
}
