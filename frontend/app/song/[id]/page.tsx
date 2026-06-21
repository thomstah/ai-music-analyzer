'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Song, LyricBreakdown } from '@/types/song';
import { getSongById } from '@/lib/api';
import LyricsPanel from '@/components/LyricsPanel';
import AnalysisPanel from '@/components/AnalysisPanel';

export default function SongPage() {
  const { id } = useParams<{ id: string }>();
  const [song, setSong] = useState<Song | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedBreakdown, setSelectedBreakdown] = useState<LyricBreakdown | null>(null);
  const [selectedLyric, setSelectedLyric] = useState<string | null>(null);

  useEffect(() => {
    const cached = sessionStorage.getItem(`song-${id}`);
    if (cached) {
      try {
        setSong(JSON.parse(cached) as Song);
        setLoading(false);
        return;
      } catch {
        // malformed cache — fall through to network fetch
      }
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
    return <div className="text-neutral-400 p-12 text-sm">Analyzing lyrics...</div>;
  }
  if (!song) {
    return <div className="text-red-400 p-12 text-sm">Song not found.</div>;
  }

  return (
    <main className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-black text-white">{song.title}</h1>
        <p className="text-neutral-400 text-lg">{song.artist}</p>
      </div>

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
          <div className="w-full lg:w-80 shrink-0 lg:sticky lg:top-6">
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
