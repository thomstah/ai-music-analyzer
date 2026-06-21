import { getTrending, searchSongs } from '@/lib/api';
import TrendingChart from '@/components/TrendingChart';
import SearchResultsList from '@/components/SearchResultsList';

export default async function HomePage({
  searchParams,
}: {
  searchParams: { q?: string };
}) {
  const query = searchParams.q?.trim() ?? '';

  if (query) {
    const results = await searchSongs(query);
    return (
      <main className="max-w-2xl mx-auto px-6 py-12">
        <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-1">
          Search results
        </p>
        <h1 className="text-2xl font-black text-white mb-8">&ldquo;{query}&rdquo;</h1>
        <SearchResultsList results={results} />
      </main>
    );
  }

  const trending = await getTrending(10);
  return (
    <main className="max-w-2xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-black text-white mb-2">What does it mean?</h1>
      <p className="text-neutral-400 mb-10">
        Search a song to get Claude&apos;s interpretation of the lyrics.
      </p>
      <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">
        Trending This Week
      </h2>
      <TrendingChart songs={trending} />
    </main>
  );
}
