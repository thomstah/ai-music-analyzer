import { LyricBreakdown } from '@/types/song';

export default function BreakdownCard({ breakdown }: { breakdown: LyricBreakdown }) {
  return (
    <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-5">
      <blockquote className="border-l-4 border-purple-600 pl-4 py-1 mb-4">
        <p className="text-white text-base italic leading-relaxed whitespace-pre-line font-serif">
          {breakdown.lyric}
        </p>
      </blockquote>
      <p className="text-neutral-300 text-sm leading-relaxed whitespace-pre-line">
        {breakdown.breakdown}
      </p>
    </div>
  );
}
