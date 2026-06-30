'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Song } from '@/types/song';
import { getSongById, deepAnalyzeSong } from '@/lib/api';
import LyricsPanel from '@/components/LyricsPanel';
import AnalysisPanel from '@/components/AnalysisPanel';
import Spinner from '@/components/Spinner';
import SongBanner from '@/components/SongBanner';

function parseCachedSong(json: string): Song | null {
  try {
    const data = JSON.parse(json) as Record<string, unknown>;
    if (typeof data?.id === 'string' && typeof data?.title === 'string') {
      return data as unknown as Song;
    }
    return null;
  } catch {
    return null;
  }
}

export default function SongPage() {
  const { id } = useParams<{ id: string }>();
  const [song, setSong] = useState<Song | null>(null);
  const [loading, setLoading] = useState(true);
  const [deepLoading, setDeepLoading] = useState(false);
  const [deepError, setDeepError] = useState<string | null>(null);

  useEffect(() => {
    const cached = sessionStorage.getItem(`song-${id}`);
    const fromCache = cached ? parseCachedSong(cached) : null;
    if (fromCache) {
      setSong(fromCache);
      setLoading(false);
      return;
    }
    getSongById(id)
      .then(data => { setSong(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [id]);

  async function handleRequestDeep() {
    if (!song || deepLoading) return;
    setDeepLoading(true);
    setDeepError(null);
    try {
      const updated = await deepAnalyzeSong(song.id);
      setSong(updated);
      sessionStorage.setItem(`song-${updated.id}`, JSON.stringify(updated));
    } catch (err: unknown) {
      setDeepError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setDeepLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-3 p-12 text-neutral-400 text-sm">
        <Spinner />
        <span>Loading song…</span>
      </div>
    );
  }
  if (!song) {
    return <div className="text-red-400 p-12 text-sm">Song not found.</div>;
  }

  return (
    <main className="max-w-6xl mx-auto px-6 py-8">
      <SongBanner song={song} />

      <div className="flex flex-col lg:flex-row gap-8 items-start">
        {/* Analysis — primary content, wider column */}
        <div className="flex-1 min-w-0 w-full">
          <AnalysisPanel
            interpretation={song.interpretation}
            commentary={song.community_commentary}
            onRequestDeepAnalysis={handleRequestDeep}
            deepAnalysisLoading={deepLoading}
            deepAnalysisError={deepError}
          />
        </div>
        {/* Lyrics — secondary column, sticky on desktop */}
        <aside className="w-full lg:w-96 shrink-0 lg:sticky lg:top-6 lg:max-h-[calc(100vh-5rem)] lg:overflow-y-auto bg-neutral-900 rounded-xl p-5">
          <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-3">
            Lyrics
          </h2>
          <LyricsPanel lyrics={song.lyrics} />
        </aside>
      </div>
    </main>
  );
}
