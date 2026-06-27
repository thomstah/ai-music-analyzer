'use client';
import { Article } from '@/types/song';

function formatTimeAgo(iso: string): string {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  if (isNaN(then)) return '';
  const minutes = Math.floor((Date.now() - then) / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function NewsPanel({ articles }: { articles: Article[] }) {
  if (articles.length === 0) {
    return (
      <p className="text-neutral-500 text-sm">
        News feed unavailable.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {articles.map(a => (
        <a
          key={a.url}
          href={a.url}
          target="_blank"
          rel="noopener noreferrer"
          className="block bg-neutral-900 hover:bg-neutral-800 rounded-lg overflow-hidden transition-colors"
        >
          <div className="flex gap-3 p-3">
            {a.image_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={a.image_url}
                alt=""
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
                className="w-20 h-20 rounded object-cover shrink-0"
              />
            )}
            <div className="min-w-0 flex-1">
              <p className="text-white font-semibold text-sm leading-snug line-clamp-2">
                {a.title}
              </p>
              <p className="text-neutral-500 text-xs mt-1">
                {a.source} · {formatTimeAgo(a.published_at)}
              </p>
            </div>
          </div>
        </a>
      ))}
    </div>
  );
}
