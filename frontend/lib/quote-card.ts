import type { Song } from '@/types/song';

export interface QuoteCardProps {
  title: string;
  artist: string;
  albumArt: string | null;
  accent: string;
  lyric: string;
  breakdown: string;
}

const DEFAULT_ACCENT = '#7c3aed';
const MAX_BREAKDOWN = 120;

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  const window = text.slice(0, max);
  // Prefer to end at the last sentence terminator inside the window so the preview
  // reads as a complete thought rather than a mid-sentence cut.
  const lastStop = Math.max(
    window.lastIndexOf('.'),
    window.lastIndexOf('!'),
    window.lastIndexOf('?'),
  );
  if (lastStop >= max * 0.6) return window.slice(0, lastStop + 1);
  return window.trimEnd() + '…';
}

export function buildQuoteCardProps(song: Song, idx: number): QuoteCardProps | null {
  const breakdowns = song.interpretation?.key_lyric_breakdowns;
  if (!breakdowns || idx < 0 || idx >= breakdowns.length) return null;
  const entry = breakdowns[idx];
  return {
    title: song.title,
    artist: song.artist,
    albumArt: song.metadata?.album_art_url ?? null,
    accent: song.metadata?.accent_color ?? DEFAULT_ACCENT,
    lyric: entry.lyric,
    breakdown: truncate(entry.breakdown, MAX_BREAKDOWN),
  };
}
