'use client';
import Spinner from '@/components/Spinner';
import { useAnalyzeProgress } from '@/hooks/useAnalyzeProgress';

export default function AnalyzeProgressPill({
  title,
  artist,
  thumbnail,
  active = true,
  compact = false,
}: {
  title: string;
  artist: string;
  thumbnail?: string | null;
  active?: boolean;
  compact?: boolean;
}) {
  const message = useAnalyzeProgress(active);
  const thumbSize = compact ? 40 : 64;

  return (
    <div className="w-full flex items-center gap-4 bg-neutral-900 rounded-lg p-3">
      {thumbnail ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={thumbnail}
          alt=""
          width={thumbSize}
          height={thumbSize}
          onError={(e) => { e.currentTarget.style.display = 'none'; }}
          className="rounded object-cover shrink-0"
          style={{ width: thumbSize, height: thumbSize }}
        />
      ) : (
        <div
          className="rounded bg-neutral-700 shrink-0"
          style={{ width: thumbSize, height: thumbSize }}
        />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-white font-semibold truncate">{title}</p>
        <p className="text-neutral-400 text-xs truncate">{artist}</p>
        <p className="text-purple-300 text-xs mt-1 truncate transition-opacity">
          {message}
        </p>
      </div>
      <Spinner size="sm" />
    </div>
  );
}
