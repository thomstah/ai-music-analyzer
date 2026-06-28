import { getArtistById } from '@/lib/api';
import ArtistBanner from '@/components/ArtistBanner';
import ArtistTopSongs from '@/components/ArtistTopSongs';
import ArtistTopAlbums from '@/components/ArtistTopAlbums';

export default async function ArtistPage({ params }: { params: { id: string } }) {
  const artist = await getArtistById(params.id);

  if (!artist) {
    return (
      <main className="max-w-6xl mx-auto px-6 py-8">
        <p className="text-red-400 text-sm">Artist not found.</p>
      </main>
    );
  }

  return (
    <main className="max-w-6xl mx-auto px-6 py-8">
      <ArtistBanner artist={artist} />

      {artist.top_songs.length > 0 && (
        <section className="mb-10">
          <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">
            Popular {artist.name} Songs
          </h2>
          <ArtistTopSongs songs={artist.top_songs} artistName={artist.name} />
        </section>
      )}

      {artist.top_albums.length > 0 && (
        <section>
          <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">
            Popular {artist.name} Albums
          </h2>
          <ArtistTopAlbums albums={artist.top_albums} artistName={artist.name} />
        </section>
      )}
    </main>
  );
}
