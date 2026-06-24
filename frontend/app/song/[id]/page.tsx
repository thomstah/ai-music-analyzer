'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Song, LyricBreakdown } from '@/types/song';
import { getSongById } from '@/lib/api';
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

  if (loading) {
    return (
      <div className="flex items-center gap-3 p-12 text-neutral-400 text-sm">
        <Spinner />
        <span>Analyzing lyrics…</span>
      </div>
    );
  }
  if (!song) {
    return <div className="text-red-400 p-12 text-sm">Song not found.</div>;
  }

  return (
    <main className="max-w-6xl mx-auto px-6 py-8">
      <SongBanner song={song} />

      {song.interpretation ? (
        <div className="flex flex-col-reverse lg:flex-row gap-8 items-start">
          {/* Lyrics — comes second in DOM so it renders below on mobile (flex-col-reverse puts analysis on top) */}
          <div className="flex-1 min-w-0">
            <LyricsPanel
              lyrics={song.lyrics}
              breakdowns={song.interpretation.key_lyric_breakdowns}
              onLineSelect={handleLineSelect}
              selectedLyric={selectedLyric}
            />
          </div>
          {/* Analysis panel — comes first visually on mobile, sticky on desktop */}
          <div className="w-full lg:w-80 shrink-0 lg:sticky lg:top-6 lg:max-h-[calc(100vh-5rem)] lg:overflow-y-auto bg-neutral-900 rounded-xl p-5">
            <AnalysisPanel
              interpretation={song.interpretation}
              commentary={song.community_commentary}
              selectedBreakdown={selectedBreakdown}
            />
          </div>
        </div>
      ) : (
        <p className="text-neutral-500">No interpretation available for this song.</p>
      )}
    </main>
  );
}
