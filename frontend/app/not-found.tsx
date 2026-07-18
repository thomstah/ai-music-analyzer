import Link from 'next/link';

export default function NotFound() {
  return (
    <main className="max-w-xl mx-auto px-6 py-24 text-center">
      <p className="text-xs font-bold text-purple-400 uppercase tracking-widest mb-3">
        404
      </p>
      <h1 className="text-3xl font-black text-white tracking-tight mb-4">
        This page isn&apos;t on the tracklist.
      </h1>
      <p className="text-neutral-400 text-sm leading-relaxed mb-8">
        The song, album, or artist you&apos;re looking for doesn&apos;t exist — or
        we haven&apos;t analyzed it yet. Try a search from home.
      </p>
      <Link
        href="/"
        className="inline-block bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium px-5 py-2.5 rounded-full transition-colors"
      >
        Back to home
      </Link>
    </main>
  );
}
