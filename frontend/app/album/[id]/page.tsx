import { getAlbumById } from '@/lib/api';
import AlbumBanner from '@/components/AlbumBanner';
import Tracklist from '@/components/Tracklist';

export default async function AlbumPage({ params }: { params: { id: string } }) {
  const album = await getAlbumById(params.id);

  if (!album) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-8">
        <p className="text-red-400 text-sm">Album not found.</p>
      </main>
    );
  }

  const accent = album.accent_color ?? null;
  const trackCount = album.tracklist.length;

  return (
    <>
      {accent && (
        <div
          aria-hidden
          className="fixed inset-x-0 top-0 h-[600px] pointer-events-none -z-10"
          style={{
            background: `linear-gradient(to bottom, ${accent} 0%, transparent 100%)`,
            opacity: 0.28,
          }}
        />
      )}
      <main className="max-w-3xl mx-auto px-6 py-8 relative">
        <AlbumBanner album={album} />

        {album.description && (
          <section className="mb-8 bg-neutral-900/60 rounded-xl p-5">
            <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-3">
              About
            </h2>
            <p className="text-neutral-200 text-sm leading-relaxed whitespace-pre-line">
              {album.description}
            </p>
          </section>
        )}

        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest">
            Tracks
          </h2>
          {trackCount > 0 && (
            <p className="text-[11px] text-neutral-500">
              {trackCount} {trackCount === 1 ? 'track' : 'tracks'}
            </p>
          )}
        </div>
        <Tracklist tracks={album.tracklist} artist={album.artist} />
      </main>
    </>
  );
}
