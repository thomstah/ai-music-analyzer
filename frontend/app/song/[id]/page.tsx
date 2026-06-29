'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Song, LyricBreakdown } from '@/types/song';
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
  const [selectedBreakdown, setSelectedBreakdown] = useState<LyricBreakdown | null>(null);
  const [selectedLyric, setSelectedLyric] = useState<string | null>(null);
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

  function handleLineSelect(breakdown: LyricBreakdown | null, rawLine: string | null) {
    setSelectedBreakdown(breakdown);
    setSelectedLyric(rawLine);
  }

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

      <div className="flex flex-col-reverse lg:flex-row gap-8 items-start">
        {/* Lyrics — second in DOM so it stacks below the analysis on mobile */}
        <div className="flex-1 min-w-0">
          <LyricsPanel
            lyrics={song.lyrics}
            breakdowns={song.interpretation?.key_lyric_breakdowns ?? []}
            onLineSelect={handleLineSelect}
            selectedLyric={selectedLyric}
          />
          {song.metadata?.musixmatch_url && (
            <p className="text-neutral-600 text-xs mt-6 italic">
              Lyrics excerpt provided by{' '}
              <a
                href={song.metadata.musixmatch_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-neutral-500 hover:text-purple-400 underline"
              >
                Musixmatch
              </a>
              . Lyriq&apos;s interpretation is AI-generated commentary.
            </p>
          )}
        </div>
        {/* Analysis panel — sticky on desktop */}
        <div className="w-full lg:w-80 shrink-0 lg:sticky lg:top-6 lg:max-h-[calc(100vh-5rem)] lg:overflow-y-auto bg-neutral-900 rounded-xl p-5">
          <AnalysisPanel
            interpretation={song.interpretation}
            commentary={song.community_commentary}
            selectedBreakdown={selectedBreakdown}
            onRequestDeepAnalysis={handleRequestDeep}
            deepAnalysisLoading={deepLoading}
            deepAnalysisError={deepError}
          />
        </div>
      </div>
    </main>
  );
}
