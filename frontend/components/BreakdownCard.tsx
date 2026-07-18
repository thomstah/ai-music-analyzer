'use client';
import { useState } from 'react';
import { LyricBreakdown } from '@/types/song';

export default function BreakdownCard({
  breakdown,
  songId,
  index,
}: {
  breakdown: LyricBreakdown;
  songId: string;
  index: number;
}) {
  const [copied, setCopied] = useState(false);

  async function handleShare() {
    const url = `${window.location.origin}/song/${songId}/breakdown/${index}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      window.prompt('Copy this link:', url);
    }
  }

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
      <button
        onClick={handleShare}
        aria-label={copied ? 'Link copied' : 'Share this breakdown'}
        title={copied ? 'Link copied' : 'Share'}
        className="mt-4 inline-flex items-center justify-center w-8 h-8 rounded-full text-neutral-500 hover:text-purple-300 hover:bg-neutral-800 transition-colors"
      >
        {copied ? (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="18" cy="5" r="3" />
            <circle cx="6" cy="12" r="3" />
            <circle cx="18" cy="19" r="3" />
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
            <line x1="15.41" y1="6.51" x2="8.59" y2="11.49" />
          </svg>
        )}
      </button>
    </div>
  );
}
