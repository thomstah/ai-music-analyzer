import { LyricBreakdown } from '@/types/song';

export default function BreakdownCard({ breakdown }: { breakdown: LyricBreakdown }) {
  return (
    <div className="bg-purple-950 border border-purple-800 rounded-lg p-4">
      <p className="text-purple-300 text-xs font-bold uppercase tracking-widest mb-2">
        Lyriq on this line
      </p>
      <blockquote className="text-neutral-300 italic text-sm mb-3 border-l-2 border-purple-600 pl-3 leading-relaxed">
        {breakdown.lyric}
      </blockquote>
      <p className="text-neutral-200 text-sm leading-relaxed">{breakdown.breakdown}</p>
    </div>
  );
}
