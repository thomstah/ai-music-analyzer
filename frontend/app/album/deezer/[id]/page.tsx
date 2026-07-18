import { getDeezerAlbum } from '@/lib/api';
import DeezerAlbumBanner from '@/components/DeezerAlbumBanner';
import DeezerTracklist from '@/components/DeezerTracklist';

export default async function DeezerAlbumPage({ params }: { params: { id: string } }) {
  const album = await getDeezerAlbum(params.id);

  if (!album) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-8">
        <p className="text-red-400 text-sm">Album not found.</p>
      </main>
    );
  }

  return (
    <main className="max-w-3xl mx-auto px-6 py-8">
      <DeezerAlbumBanner album={album} />

      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest">
          Tracks
        </h2>
        <p className="text-[11px] text-neutral-500">
          Click any track to analyze — it&apos;ll join our library.
        </p>
      </div>
      <DeezerTracklist tracks={album.tracks} artist={album.artist} />
    </main>
  );
}
