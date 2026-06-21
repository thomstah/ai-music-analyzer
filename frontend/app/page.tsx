import { getTrending } from '@/lib/api';
import TrendingChart from '@/components/TrendingChart';

export default async function HomePage() {
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
