import { getBillboard, searchSongs, getMusicNews, getTrendingThemes } from '@/lib/api';
import BillboardChart from '@/components/BillboardChart';
import NewsPanel from '@/components/NewsPanel';
import TrendingThemes from '@/components/TrendingThemes';
import SearchResultsList from '@/components/SearchResultsList';
import FeaturedArtistBanner from '@/components/FeaturedArtistBanner';

export default async function HomePage({
  searchParams,
}: {
  searchParams: { q?: string };
}) {
  const query = searchParams.q?.trim() ?? '';

  if (query) {
    const results = await searchSongs(query);
    return (
      <main className="max-w-6xl mx-auto px-6 py-12">
        <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-1">
          Search results
        </p>
        <h1 className="text-2xl font-black text-white mb-8">&ldquo;{query}&rdquo;</h1>
        <SearchResultsList results={results} />
      </main>
    );
  }

  const [billboard, articles, themes] = await Promise.all([
    getBillboard(10),
    getMusicNews(4),
    getTrendingThemes(8),
  ]);
  return (
    <main className="max-w-6xl mx-auto px-6 py-6">
      <h1 className="text-2xl font-black text-white mb-1">What does it mean?</h1>
      <p className="text-neutral-400 text-sm mb-4">
        Search a song to get Lyriq&apos;s interpretation of the lyrics.
      </p>
      <FeaturedArtistBanner songs={billboard} />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <section className="lg:col-span-2">
          <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-3">
            Billboard Hot 100
          </h2>
          <BillboardChart songs={billboard} />
        </section>
        <aside className="space-y-6">
          <div>
            <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-3">
              Music News
            </h2>
            <NewsPanel articles={articles} />
          </div>
          <div>
            <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-3">
              Trending Themes
            </h2>
            <TrendingThemes themes={themes} />
          </div>
        </aside>
      </div>
    </main>
  );
}
