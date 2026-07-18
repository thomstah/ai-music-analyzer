'use client';
import { useState, useMemo, useEffect } from 'react';
import Link from 'next/link';
import { Interpretation, DiscourseExcerpt } from '@/types/song';
import BreakdownCard from './BreakdownCard';
import Spinner from './Spinner';

export type DeepError =
  | { kind: 'generic'; message: string }
  | { kind: 'rate-limited'; retryAfter: number }
  | { kind: 'budget-out'; resetsOn: string | null };

interface Props {
  interpretation: Interpretation | null;
  commentary: DiscourseExcerpt[] | null;
  songId: string;
  onRequestDeepAnalysis?: () => void;
  deepAnalysisLoading?: boolean;
  deepAnalysisError?: DeepError | null;
}

export default function AnalysisPanel({
  interpretation,
  commentary,
  songId,
  onRequestDeepAnalysis,
  deepAnalysisLoading,
  deepAnalysisError,
}: Props) {
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
    <article className="space-y-8">
      {/* Deep analysis CTA — shown only when no interpretation exists yet */}
      {!interpretation && onRequestDeepAnalysis && (
        <div>
          <button
            onClick={onRequestDeepAnalysis}
            disabled={deepAnalysisLoading}
            className="group w-full flex items-center justify-center gap-2 border border-dashed border-purple-700/70 hover:border-purple-500 hover:bg-purple-950/30 disabled:opacity-60 disabled:cursor-not-allowed text-purple-200 hover:text-white text-sm font-medium py-6 rounded-xl transition-colors"
          >
            {deepAnalysisLoading ? (
              <Spinner size="sm" />
            ) : (
              <>
                <span aria-hidden className="text-purple-400 group-hover:text-purple-200 transition-colors">✦</span>
                <span>Lyriq Deep Analysis</span>
              </>
            )}
          </button>
          {deepAnalysisError && (
            <div className="mt-3 border border-amber-700/50 bg-amber-950/30 rounded-lg p-3">
              {deepAnalysisError.kind === 'budget-out' ? (
                <p className="text-amber-200 text-sm">
                  Lyriq&apos;s monthly analysis budget is out.
                  {deepAnalysisError.resetsOn && ` New analyses resume on ${deepAnalysisError.resetsOn}.`}
                  {' '}Existing analyses across the site still work.
                </p>
              ) : deepAnalysisError.kind === 'rate-limited' ? (
                <p className="text-amber-200 text-sm">
                  You&apos;re going a bit fast. Try again in about {deepAnalysisError.retryAfter}s.
                </p>
              ) : (
                <p className="text-red-400 text-sm">{deepAnalysisError.message}</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Deep analysis content */}
      {interpretation && (
        <>
          {/* TL;DR */}
          {interpretation.tldr && (
            <section id="tldr" className="scroll-mt-16">
              <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-2">
                TL;DR
              </p>
              <p className="text-white text-lg leading-relaxed font-medium">
                {interpretation.tldr}
              </p>
            </section>
          )}

          {/* Tone + Themes side-by-side on wider screens */}
          <section id="essence" className="scroll-mt-16 grid grid-cols-1 sm:grid-cols-2 gap-6 items-stretch">
            <div className="flex flex-col">
              <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-2">
                Emotional Tone
              </p>
              <div className="flex-1 bg-neutral-800 text-purple-300 text-sm font-medium px-4 py-3 rounded-md flex items-center leading-relaxed">
                {interpretation.emotional_tone}
              </div>
            </div>
            <div className="flex flex-col">
              <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-2">
                Themes
              </p>
              <div className="flex flex-wrap gap-2 content-start">
                {interpretation.themes.map(theme => (
                  <Link
                    key={theme}
                    href={`/theme/${encodeURIComponent(theme)}`}
                    className="bg-neutral-800 hover:bg-neutral-700 text-neutral-300 hover:text-white text-sm px-2.5 py-1 rounded transition-colors"
                  >
                    {theme}
                  </Link>
                ))}
              </div>
            </div>
          </section>

          {/* Meaning */}
          <section id="meaning" className="scroll-mt-16">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest">
                Meaning
              </p>
              {interpretation.tldr && (
                <button
                  onClick={() => setSummaryExpanded(v => !v)}
                  aria-expanded={summaryExpanded}
                  className="text-purple-400 text-xs hover:underline"
                >
                  {summaryExpanded ? 'Collapse' : 'Read full analysis'}
                </button>
              )}
            </div>
            <p className="text-neutral-300 text-base leading-relaxed whitespace-pre-line">
              {summaryExpanded || !interpretation.tldr
                ? interpretation.overall_meaning
                : interpretation.overall_meaning.split('\n\n')[0]}
            </p>
          </section>

          {/* Line-by-line breakdowns */}
          {interpretation.key_lyric_breakdowns.length > 0 && (
            <section id="key-lines" className="scroll-mt-16">
              <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">
                Key Lines
              </p>
              <div className="space-y-4">
                {interpretation.key_lyric_breakdowns.map((bd, i) => (
                  <BreakdownCard key={i} breakdown={bd} songId={songId} index={i} />
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {/* Community commentary */}
      {sortedCommentary.length > 0 && (
        <section id="community" className="scroll-mt-16">
          <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-3">
            Community
          </p>
          <div className="space-y-3">
            {sortedCommentary.map((exc, i) => (
              <div key={`${exc.source}-${i}`} className="bg-neutral-900 rounded-lg p-4 border border-neutral-800">
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
        </section>
      )}
    </article>
  );
}
