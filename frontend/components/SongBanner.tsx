import { Song } from '@/types/song';

export default function SongBanner({ song }: { song: Song }) {
  const meta = song.metadata;
  const albumArt = meta?.album_art_url ?? null;

  return (
    <div className="relative overflow-hidden rounded-xl mb-8 min-h-48">
      {/* Blurred album art background */}
      {albumArt && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={albumArt}
          alt=""
          aria-hidden
          className="absolute inset-0 w-full h-full object-cover scale-110 blur-2xl opacity-50"
        />
      )}
      {/* Dark gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/50 to-neutral-950" />

      {/* Content */}
      <div className="relative z-10 flex gap-6 p-6 items-end">
        {albumArt && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={albumArt}
            alt={`${song.title} album art`}
            width={120}
            height={120}
            className="rounded-lg shadow-2xl shrink-0 hidden sm:block"
          />
        )}
        <div className="min-w-0">
          <h1 className="text-3xl font-black text-white leading-tight">{song.title}</h1>
          <p className="text-neutral-300 text-lg mt-1">{song.artist}</p>
          <div className="flex flex-wrap gap-x-6 gap-y-1 mt-3 text-xs text-neutral-400">
            {meta?.album_name && (
              <span><span className="text-neutral-500">Album</span> {meta.album_name}</span>
            )}
            {meta?.release_year && (
              <span><span className="text-neutral-500">Year</span> {meta.release_year}</span>
            )}
            {meta?.producer && (
              <span><span className="text-neutral-500">Produced by</span> {meta.producer}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
