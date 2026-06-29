'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArtistTopSong, Song } from '@/types/song';
import { analyzeSong } from '@/lib/api';
import Spinner from '@/components/Spinner';

export default function ArtistTopSongs({
  songs,
  artistName,
}: {
  songs: ArtistTopSong[];
  artistName: string;
}) {
  const router = useRouter();
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (songs.length === 0) {
    return <p className="text-neutral-500 text-sm">No popular songs found.</p>;
  }

  async function handleSelect(s: ArtistTopSong) {
    if (loadingId !== null) return;
    setLoadingId(s.genius_id);
    setError(null);
    try {
      // Use the song's actual primary artist (e.g. "Rihanna" for Work feat. Drake),
      // not the page artist. Otherwise Genius returns a same-name match (Drake White, etc.).
      const song: Song = await analyzeSong(s.title, s.artist_name || artistName);
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
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {songs.map(s => (
          <button
            key={s.genius_id}
            onClick={() => handleSelect(s)}
            disabled={loadingId !== null}
            className="flex items-center gap-4 bg-neutral-900 hover:bg-neutral-800 disabled:opacity-60 rounded-lg p-3 transition-colors text-left"
          >
            {s.thumbnail ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={s.thumbnail}
                alt=""
                width={56}
                height={56}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
                className="w-14 h-14 rounded object-cover shrink-0"
              />
            ) : (
              <div className="w-14 h-14 rounded bg-neutral-700 shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-white font-semibold truncate">{s.title}</p>
              <p className="text-neutral-400 text-sm truncate">{s.artist_name}</p>
            </div>
            <div className="w-4 h-4 shrink-0 flex items-center justify-center">
              {loadingId === s.genius_id && <Spinner size="sm" />}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
