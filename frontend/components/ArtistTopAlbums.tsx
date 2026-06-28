'use client';
import Link from 'next/link';
import { ArtistTopAlbum } from '@/types/song';

export default function ArtistTopAlbums({
  albums,
  artistName,
}: {
  albums: ArtistTopAlbum[];
  artistName: string;
}) {
  if (albums.length === 0) {
    return <p className="text-neutral-500 text-sm">No popular albums found.</p>;
  }
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4">
      {albums.map(a => (
        <Link
          key={a.album_id_deezer}
          href={`/?q=${encodeURIComponent(`${artistName} ${a.title}`)}`}
          className="block group"
        >
          {a.cover_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={a.cover_url}
              alt={a.title}
              width={200}
              height={200}
              onError={(e) => { e.currentTarget.style.display = 'none'; }}
              className="w-full aspect-square rounded-lg object-cover shadow-lg group-hover:opacity-80 transition-opacity"
            />
          ) : (
            <div className="w-full aspect-square rounded-lg bg-neutral-800" />
          )}
          <p className="text-white text-sm font-medium mt-2 truncate group-hover:text-purple-300 transition-colors">
            {a.title}
          </p>
          {a.release_year && (
            <p className="text-neutral-500 text-xs">{a.release_year}</p>
          )}
        </Link>
      ))}
    </div>
  );
}
