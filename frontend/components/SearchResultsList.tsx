'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { SearchResults, SearchResult, ArtistResult, AlbumSearchResult, Song } from '@/types/song';
import { analyzeSong } from '@/lib/api';
import Spinner from '@/components/Spinner';

function SectionHeader({ label }: { label: string }) {
  return (
    <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-3 mt-8 first:mt-0">
      {label}
    </p>
  );
}

function ArtistRow({ artist }: { artist: ArtistResult }) {
  return (
    <Link
      href={`/artist/${artist.artist_id}`}
      className="w-full flex items-center gap-4 bg-neutral-900 hover:bg-neutral-800 rounded-lg px-4 py-3 transition-colors text-left"
    >
      {artist.thumbnail ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={artist.thumbnail}
          alt=""
          width={40}
          height={40}
          className="w-10 h-10 rounded-full object-cover shrink-0"
        />
      ) : (
        <div className="w-10 h-10 rounded-full bg-neutral-700 shrink-0 flex items-center justify-center">
          <span className="text-neutral-400 text-lg font-bold">{artist.name[0]}</span>
        </div>
      )}
      <p className="text-white font-semibold truncate">{artist.name}</p>
    </Link>
  );
}

function SongRow({
  result,
  loading,
  onClick,
}: {
  result: SearchResult;
  loading: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="w-full flex items-center gap-4 bg-neutral-900 hover:bg-neutral-800 disabled:opacity-60 rounded-lg px-4 py-3 transition-colors text-left"
    >
      {result.thumbnail ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={result.thumbnail}
          alt=""
          width={40}
          height={40}
          className="w-10 h-10 rounded object-cover shrink-0"
        />
      ) : (
        <div className="w-10 h-10 rounded bg-neutral-700 shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-white font-semibold truncate">{result.title}</p>
        <p className="text-neutral-400 text-sm truncate">{result.artist}</p>
      </div>
      <div className="w-4 h-4 shrink-0 flex items-center justify-center">
        {loading && <Spinner size="sm" />}
      </div>
    </button>
  );
}

function SongCard({
  result,
  loading,
  onClick,
}: {
  result: SearchResult;
  loading: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="flex items-center gap-4 bg-neutral-900 hover:bg-neutral-800 disabled:opacity-60 rounded-lg p-3 transition-colors text-left"
    >
      {result.thumbnail ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={result.thumbnail}
          alt=""
          width={64}
          height={64}
          className="w-16 h-16 rounded object-cover shrink-0"
        />
      ) : (
        <div className="w-16 h-16 rounded bg-neutral-700 shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-white font-semibold truncate">{result.title}</p>
        <p className="text-neutral-400 text-sm truncate">{result.artist}</p>
      </div>
      <div className="w-4 h-4 shrink-0 flex items-center justify-center">
        {loading && <Spinner size="sm" />}
      </div>
    </button>
  );
}

function AlbumCard({ album }: { album: AlbumSearchResult }) {
  return (
    <Link
      href={`/album/${album.album_id}`}
      className="flex items-center gap-4 bg-neutral-900 hover:bg-neutral-800 rounded-lg p-3 transition-colors"
    >
      {album.thumbnail ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={album.thumbnail}
          alt=""
          width={64}
          height={64}
          onError={(e) => { e.currentTarget.style.display = 'none'; }}
          className="w-16 h-16 rounded object-cover shrink-0"
        />
      ) : (
        <div className="w-16 h-16 rounded bg-neutral-700 shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-white font-semibold truncate">{album.name}</p>
        <p className="text-neutral-400 text-sm truncate">{album.artist}</p>
      </div>
    </Link>
  );
}

export default function SearchResultsList({ results }: { results: SearchResults }) {
  const router = useRouter();
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isEmpty =
    results.songs.length === 0 &&
    results.lyrics.length === 0 &&
    results.artists.length === 0 &&
    results.albums.length === 0;

  if (isEmpty) {
    return (
      <p className="text-neutral-500 text-sm">
        No results found. Try different words or check the spelling.
      </p>
    );
  }

  async function handleSongSelect(result: SearchResult) {
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
    <div>
      {error && <p className="text-red-400 text-xs mb-4">{error}</p>}

      <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-8">
        {/* Left sidebar — Artists */}
        {results.artists.length > 0 && (
          <div>
            <SectionHeader label="Artists" />
            <div className="space-y-2">
              {results.artists.map(a => (
                <ArtistRow
                  key={a.artist_id}
                  artist={a}
                />
              ))}
            </div>
          </div>
        )}

        {/* Main column — Songs grid + Albums + Lyrics */}
        <div className={results.artists.length > 0 ? '' : 'lg:col-span-2'}>
          {results.songs.length > 0 && (
            <div>
              <SectionHeader label="Songs" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {results.songs.map(s => (
                  <SongCard
                    key={s.genius_id}
                    result={s}
                    loading={loadingId === s.genius_id}
                    onClick={() => handleSongSelect(s)}
                  />
                ))}
              </div>
            </div>
          )}

          {results.albums.length > 0 && (
            <div className="mt-8">
              <SectionHeader label="Albums" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {results.albums.map(a => (
                  <AlbumCard key={a.album_id} album={a} />
                ))}
              </div>
            </div>
          )}

          {results.lyrics.length > 0 && (
            <div className="mt-8">
              <SectionHeader label="Lyrics" />
              <div className="space-y-2">
                {results.lyrics.map(s => (
                  <SongRow
                    key={s.genius_id}
                    result={s}
                    loading={loadingId === s.genius_id}
                    onClick={() => handleSongSelect(s)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
