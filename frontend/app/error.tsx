'use client';
import { useEffect } from 'react';
import Link from 'next/link';

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Lyriq error boundary:', error);
  }, [error]);

  return (
    <main className="max-w-xl mx-auto px-6 py-24 text-center">
      <p className="text-xs font-bold text-purple-400 uppercase tracking-widest mb-3">
        Something broke
      </p>
      <h1 className="text-3xl font-black text-white tracking-tight mb-4">
        Lyriq hit a snag.
      </h1>
      <p className="text-neutral-400 text-sm leading-relaxed mb-8">
        It&apos;s not you — something on our end went sideways. Try again in a
        second, and if it keeps happening, head home and pick a different song.
      </p>

      <div className="flex justify-center gap-3">
        <button
          onClick={reset}
          className="bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium px-5 py-2.5 rounded-full transition-colors"
        >
          Try again
        </button>
        <Link
          href="/"
          className="border border-neutral-700 hover:border-neutral-500 text-neutral-300 hover:text-white text-sm font-medium px-5 py-2.5 rounded-full transition-colors"
        >
          Go home
        </Link>
      </div>

      {error.digest && (
        <p className="mt-10 text-[10px] font-mono text-neutral-600">
          ref {error.digest}
        </p>
      )}
    </main>
  );
}
