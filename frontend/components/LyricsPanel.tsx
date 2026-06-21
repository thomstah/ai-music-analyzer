'use client';
import { LyricBreakdown } from '@/types/song';

interface Props {
  lyrics: string;
  breakdowns: LyricBreakdown[];
  onLineSelect: (breakdown: LyricBreakdown | null) => void;
  selectedLyric: string | null;
}

export default function LyricsPanel({ lyrics, breakdowns, onLineSelect, selectedLyric }: Props) {
  const lines = lyrics.split('\n');

  function findBreakdown(line: string): LyricBreakdown | null {
    const normalized = line.trim().toLowerCase();
    if (!normalized) return null;
    return (
      breakdowns.find(b => {
        const bd = b.lyric.toLowerCase();
        return bd.includes(normalized) || normalized.includes(bd);
      }) ?? null
    );
  }

  return (
    <div className="font-mono text-sm leading-8">
      {lines.map((line, i) => {
        const bd = findBreakdown(line);
        const hasBreakdown = !!bd;
        const isSelected = selectedLyric === line.trim() && hasBreakdown;

        return (
          <p
            key={i}
            onClick={() => onLineSelect(hasBreakdown ? bd : null)}
            className={[
              'px-2 py-0.5 rounded transition-colors',
              line.trim() === '' ? 'h-5' : 'cursor-pointer',
              isSelected
                ? 'bg-purple-950 text-purple-200'
                : hasBreakdown
                ? 'text-white underline decoration-purple-500 decoration-dotted underline-offset-4 hover:bg-purple-950/40'
                : 'text-neutral-300 hover:bg-neutral-800',
            ]
              .filter(Boolean)
              .join(' ')}
          >
            {line || ' '}
          </p>
        );
      })}
    </div>
  );
}
