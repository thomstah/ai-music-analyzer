import Link from 'next/link';
import { TrendingSong } from '@/types/song';

export default function TrendingChart({ songs }: { songs: TrendingSong[] }) {
  if (songs.length === 0) {
    return (
      <p className="text-neutral-500 text-sm">
        No songs analyzed yet. Search for one above to get started.
      </p>
    );
  }
  return (
    <ol className="space-y-2">
      {songs.map((song, i) => (
        <li key={song.id}>
          <Link
            href={`/song/${song.id}`}
            className="flex items-center gap-4 bg-neutral-900 hover:bg-neutral-800 rounded-lg px-4 py-3 transition-colors"
          >
            <span className="text-neutral-600 font-bold w-5 text-right text-sm">{i + 1}</span>
            <div className="flex-1 min-w-0">
              <p className="text-white font-semibold truncate">{song.title}</p>
              <p className="text-neutral-400 text-sm truncate">{song.artist}</p>
            </div>
            <span className="text-purple-400 text-sm font-medium shrink-0">
              {song.request_count.toLocaleString()} views
            </span>
          </Link>
        </li>
      ))}
    </ol>
  );
}
