import Link from 'next/link';
import { getSongsByTheme } from '@/lib/api';
import { ThemeSongResult } from '@/types/song';

function titleCase(theme: string): string {
  return theme
    .split(/[\s-]+/)
    .map(w => (w.length > 0 ? w[0].toUpperCase() + w.slice(1) : w))
    .join(' ');
}

function ThemeSongCard({ song }: { song: ThemeSongResult }) {
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

export default async function ThemePage({ params }: { params: { name: string } }) {
  const themeRaw = decodeURIComponent(params.name);
  const themeDisplay = titleCase(themeRaw);
  const songs = await getSongsByTheme(themeRaw, 30);

  return (
    <main className="max-w-6xl mx-auto px-6 py-8">
      <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-2">Theme</p>
      <h1 className="text-3xl font-black text-white mb-1">{themeDisplay}</h1>
      <p className="text-neutral-400 text-sm mb-8">
        {songs.length === 0
          ? 'No songs in the corpus yet are tagged with this theme.'
          : `${songs.length} ${songs.length === 1 ? 'song' : 'songs'} tagged with this theme`}
      </p>

      {songs.length === 0 ? (
        <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-6 text-neutral-400 text-sm leading-relaxed">
          <p className="mb-2">
            Themes are tagged by Claude when a song is analyzed. Once more songs are
            analyzed and happen to share this theme, they&apos;ll show up here.
          </p>
          <p>
            <Link href="/" className="text-purple-400 hover:underline">
              ← Back to home
            </Link>
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {songs.map(song => (
            <ThemeSongCard key={song.id} song={song} />
          ))}
        </div>
      )}
    </main>
  );
}
