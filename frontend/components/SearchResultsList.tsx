'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { SearchResult, Song } from '@/types/song';
import { analyzeSong } from '@/lib/api';

export default function SearchResultsList({ results }: { results: SearchResult[] }) {
  const router = useRouter();
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (results.length === 0) {
    return (
      <p className="text-neutral-500 text-sm">
        No songs found. Try different words or check the spelling.
      </p>
    );
  }

  async function handleSelect(result: SearchResult) {
    if (loadingId !== null) return;
    setLoadingId(result.genius_id);
    setError(null);
    try {
      const song: Song = await analyzeSong(result.title, result.artist);
      sessionStorage.setItem(`song-${song.id}`, JSON.stringify(song));
      router.push(`/song/${song.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setLoadingId(null);
    }
  }

  return (
    <div className="space-y-2">
      {error && <p className="text-red-400 text-xs mb-3">{error}</p>}
      {results.map(result => (
        <button
          key={result.genius_id}
          onClick={() => handleSelect(result)}
          disabled={loadingId !== null}
          className="w-full flex items-center gap-4 bg-neutral-900 hover:bg-neutral-800 disabled:opacity-60 rounded-lg px-4 py-3 transition-colors text-left"
        >
          {result.thumbnail ? (
            <Image
              src={result.thumbnail}
              alt=""
              width={40}
              height={40}
              className="rounded object-cover shrink-0"
            />
          ) : (
            <div className="w-10 h-10 rounded bg-neutral-700 shrink-0" />
          )}
          <div className="flex-1 min-w-0">
            <p className="text-white font-semibold truncate">{result.title}</p>
            <p className="text-neutral-400 text-sm truncate">{result.artist}</p>
          </div>
          {loadingId === result.genius_id && (
            <span className="text-purple-400 text-xs shrink-0">Analyzing…</span>
          )}
        </button>
      ))}
    </div>
  );
}
