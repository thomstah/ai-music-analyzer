'use client';
import Link from 'next/link';
import { ThemeSongResult } from '@/types/song';

export default function ThemeSongCard({ song }: { song: ThemeSongResult }) {
  const art = song.metadata?.album_art_url ?? null;
  return (
    <Link
      href={`/song/${song.id}`}
      className="bg-neutral-900 hover:bg-neutral-800 rounded-xl overflow-hidden border border-neutral-800 transition-colors group flex flex-col"
    >
      {art ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={art}
          alt=""
          onError={(e) => { e.currentTarget.style.display = 'none'; }}
          className="w-full aspect-square object-cover"
        />
      ) : (
        <div className="w-full aspect-square bg-neutral-800 flex items-center justify-center">
          <span className="text-neutral-600 text-xs uppercase tracking-widest">No art</span>
        </div>
      )}
      <div className="p-4 flex-1 flex flex-col">
        <p className="text-white font-semibold truncate group-hover:text-purple-300 transition-colors">
          {song.title}
        </p>
        <p className="text-neutral-400 text-sm truncate">{song.artist}</p>
        {song.tldr && (
          <p className="text-neutral-500 text-xs leading-relaxed mt-3 line-clamp-3">
            {song.tldr}
          </p>
        )}
      </div>
    </Link>
  );
}
