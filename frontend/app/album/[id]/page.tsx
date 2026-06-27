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

  return (
    <main className="max-w-3xl mx-auto px-6 py-8">
      <AlbumBanner album={album} />

      <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">
        Tracks
      </h2>
      <Tracklist tracks={album.tracklist} artist={album.artist} />
    </main>
  );
}
