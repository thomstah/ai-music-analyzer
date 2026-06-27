import Link from 'next/link';
import { TrendingTheme } from '@/types/song';

export default function TrendingThemes({ themes }: { themes: TrendingTheme[] }) {
  if (themes.length === 0) {
    return (
      <p className="text-neutral-500 text-sm">
        Analyze a few songs to see trending themes.
      </p>
    );
  }
  return (
    <div className="flex flex-wrap gap-2">
      {themes.map(t => (
        <Link
          key={t.theme}
          href={`/?q=${encodeURIComponent(t.theme)}`}
          className="bg-neutral-900 hover:bg-neutral-800 text-neutral-300 text-sm px-3 py-1.5 rounded-full transition-colors"
        >
          {t.theme}
          <span className="text-neutral-500 text-xs ml-2">{t.count}</span>
        </Link>
      ))}
    </div>
  );
}
