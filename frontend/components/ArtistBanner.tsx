'use client';
import { Artist } from '@/types/song';

export default function ArtistBanner({ artist }: { artist: Artist }) {
  const header = artist.header_image_url;
  const photo = artist.image_url;

  return (
    <div className="relative overflow-hidden rounded-xl mb-8 min-h-56">
      {/* Header background */}
      {header && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={header}
          alt=""
          aria-hidden
          className="absolute inset-0 w-full h-full object-cover scale-110 blur-xl opacity-40"
        />
      )}
      <div className="absolute inset-0 bg-gradient-to-b from-black/70 via-black/60 to-neutral-950" />

      <div className="relative z-10 flex flex-col sm:flex-row items-center sm:items-end gap-6 p-6">
        {photo && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={photo}
            alt={`${artist.name} photo`}
            width={140}
            height={140}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
            className="rounded-full shadow-2xl object-cover w-32 h-32 sm:w-36 sm:h-36 shrink-0 ring-2 ring-neutral-700"
          />
        )}
        <div className="min-w-0 text-center sm:text-left">
          <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest mb-1">Artist</p>
          <h1 className="text-4xl font-black text-white leading-tight">{artist.name}</h1>
          {artist.alternate_names.length > 0 && (
            <p className="text-neutral-400 text-sm mt-1">
              <span className="text-neutral-500">AKA</span> {artist.alternate_names.join(', ')}
            </p>
          )}
          {artist.description_preview && (
            <p className="text-neutral-300 text-sm leading-relaxed mt-3 max-w-2xl">
              {artist.description_preview}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
