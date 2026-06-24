'use client';
import { useState, useMemo, useEffect } from 'react';
import { Interpretation, DiscourseExcerpt, LyricBreakdown } from '@/types/song';
import BreakdownCard from './BreakdownCard';

interface Props {
  interpretation: Interpretation;
  commentary: DiscourseExcerpt[] | null;
  selectedBreakdown: LyricBreakdown | null;
}

export default function AnalysisPanel({ interpretation, commentary, selectedBreakdown }: Props) {
  const [summaryExpanded, setSummaryExpanded] = useState(false);

  useEffect(() => {
    setSummaryExpanded(false);
  }, [interpretation]);

  const sortedCommentary = useMemo(() => {
    if (!commentary) return [];
    return [...commentary].sort((a, b) => {
      if (a.source === 'genius' && b.source !== 'genius') return -1;
      if (b.source === 'genius' && a.source !== 'genius') return 1;
      return 0;
    });
  }, [commentary]);

  return (
    <div className="space-y-6">
      {/* Emotional tone */}
      <div>
        <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-2">
          Emotional Tone
        </p>
        <span className="inline-block bg-neutral-800 text-purple-300 text-xs font-medium px-3 py-1 rounded-full">
          {interpretation.emotional_tone}
        </span>
      </div>

      {/* Themes */}
      <div>
        <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-2">Themes</p>
        <div className="flex flex-wrap gap-2">
          {interpretation.themes.map(theme => (
            <span
              key={theme}
              className="bg-neutral-800 text-neutral-300 text-xs px-2 py-1 rounded"
            >
              {theme}
            </span>
          ))}
        </div>
      </div>

      {/* TL;DR / Overall meaning */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest">
            Meaning
          </p>
          {interpretation.tldr && (
            <button
              onClick={() => setSummaryExpanded(v => !v)}
              aria-expanded={summaryExpanded}
              aria-label={summaryExpanded ? 'Show brief summary' : 'Show full analysis'}
              className="text-purple-400 text-xs hover:underline"
            >
              {summaryExpanded ? 'TL;DR ↑' : 'Full analysis ↓'}
            </button>
          )}
        </div>

        {interpretation.tldr && !summaryExpanded ? (
          <p className="text-neutral-200 text-sm leading-relaxed font-medium">
            {interpretation.tldr}
          </p>
        ) : (
          <p className="text-neutral-300 text-sm leading-relaxed whitespace-pre-line">
            {interpretation.overall_meaning}
          </p>
        )}
      </div>

      {/* Selected lyric breakdown */}
      {selectedBreakdown && (
        <div>
          <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-2">
            Line Breakdown
          </p>
          <BreakdownCard breakdown={selectedBreakdown} />
        </div>
      )}

      {/* Community commentary */}
      {sortedCommentary.length > 0 && (
        <div>
          <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-3">
            Community
          </p>
          <div className="space-y-3">
            {sortedCommentary.map((exc, i) => (
              <div key={`${exc.source}-${i}`} className="bg-neutral-900 rounded-lg p-3 border border-neutral-800">
                <p className="text-xs text-neutral-500 mb-1 uppercase tracking-wide font-medium">
                  {exc.source}
                </p>
                <p className="text-neutral-300 text-sm leading-relaxed">{exc.text}</p>
                {exc.url && (
                  <a
                    href={exc.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-purple-400 text-xs mt-1 inline-block hover:underline"
                  >
                    View source ↗
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
