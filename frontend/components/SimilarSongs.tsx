'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { SimilarSong } from '@/types/song';
import { getSimilarSongs } from '@/lib/api';

export default function SimilarSongs({ songId }: { songId: string }) {
  const [items, setItems] = useState<SimilarSong[] | null>(null);

  useEffect(() => {
    let alive = true;
    getSimilarSongs(songId, 3).then((list) => {
      if (alive) setItems(list);
    });
    return () => {
      alive = false;
    };
  }, [songId]);

  if (!items || items.length === 0) return null;

  return (
    <section className="mt-10">
      <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">
        If you liked this
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {items.map((s) => (
          <Link
            key={s.id}
            href={`/song/${s.id}`}
            className="flex items-center gap-3 bg-neutral-900 hover:bg-neutral-800 rounded-lg p-3 transition-colors"
          >
            {s.thumbnail ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={s.thumbnail}
                alt=""
                width={48}
                height={48}
                onError={(e) => {
                  e.currentTarget.style.display = 'none';
                }}
                className="w-12 h-12 rounded object-cover shrink-0"
              />
            ) : (
              <div className="w-12 h-12 rounded bg-neutral-700 shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-semibold truncate">{s.title}</p>
              <p className="text-neutral-400 text-xs truncate">{s.artist}</p>
              <p className="text-purple-400 text-[10px] uppercase tracking-widest mt-0.5 truncate">
                shares: {s.shared_themes.slice(0, 2).join(', ')}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
