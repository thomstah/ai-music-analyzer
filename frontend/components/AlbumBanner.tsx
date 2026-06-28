'use client';
import Link from 'next/link';
import { Album } from '@/types/song';

export default function AlbumBanner({ album }: { album: Album }) {
  const cover = album.cover_art_url;
  return (
    <div className="relative overflow-hidden rounded-xl mb-8 min-h-48">
      {cover && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={cover}
          alt=""
          aria-hidden
          className="absolute inset-0 w-full h-full object-cover scale-110 blur-2xl opacity-50"
        />
      )}
      <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/50 to-neutral-950" />
      <div className="relative z-10 flex gap-6 p-6 items-end">
        {cover && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={cover}
            alt={`${album.title} cover`}
            width={140}
            height={140}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
            className="rounded-lg shadow-2xl shrink-0 hidden sm:block"
          />
        )}
        <div className="min-w-0">
          <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest mb-1">Album</p>
          <h1 className="text-3xl font-black text-white leading-tight">{album.title}</h1>
          {album.artist_id ? (
            <Link
              href={`/artist/${album.artist_id}`}
              className="text-neutral-300 text-lg mt-1 inline-block hover:text-purple-300 transition-colors"
            >
              {album.artist}
            </Link>
          ) : (
            <p className="text-neutral-300 text-lg mt-1">{album.artist}</p>
          )}
          <div className="flex flex-wrap gap-x-6 gap-y-1 mt-3 text-xs text-neutral-400">
            {album.release_year && (
              <span><span className="text-neutral-500">Year</span> {album.release_year}</span>
            )}
            {album.producers.length > 0 && (
              <span><span className="text-neutral-500">Produced by</span> {album.producers.join(', ')}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
