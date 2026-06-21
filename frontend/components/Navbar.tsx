'use client';
import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';

export default function Navbar() {
  const router = useRouter();
  const [query, setQuery] = useState('');

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    router.push(`/?q=${encodeURIComponent(q)}`);
  }

  return (
    <nav className="bg-neutral-950 border-b border-neutral-800 px-6 py-3">
      <div className="max-w-6xl mx-auto flex items-center gap-6">
        <a href="/" className="text-purple-400 font-black text-lg tracking-widest shrink-0">
          LYRIQ
        </a>
        <form onSubmit={handleSearch} className="flex gap-2 flex-1 max-w-xl">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Song, artist, or lyric…"
            className="flex-1 bg-neutral-800 text-white placeholder-neutral-500 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-purple-500"
          />
          <button
            type="submit"
            className="bg-purple-600 hover:bg-purple-500 text-white text-sm px-4 py-1.5 rounded font-medium transition-colors"
          >
            Search
          </button>
        </form>
      </div>
    </nav>
  );
}
