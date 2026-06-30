'use client';
import { useEffect, useState } from 'react';

export interface SectionLink {
  id: string;
  label: string;
}

interface Props {
  sections: SectionLink[];
}

/**
 * Mobile-only sticky pill bar that links to anchored sections within the page.
 * Highlights the section currently nearest the top of the viewport using
 * IntersectionObserver.
 */
export default function SongSectionNav({ sections }: Props) {
  const [activeId, setActiveId] = useState<string | null>(sections[0]?.id ?? null);

  useEffect(() => {
    if (sections.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter(e => e.isIntersecting);
        if (visible.length === 0) return;
        // Choose whichever visible section is closest to the top of the viewport.
        const topMost = visible.reduce((a, b) =>
          a.boundingClientRect.top < b.boundingClientRect.top ? a : b
        );
        setActiveId(topMost.target.id);
      },
      { rootMargin: '-15% 0px -65% 0px', threshold: 0 },
    );

    sections.forEach(s => {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [sections]);

  if (sections.length === 0) return null;

  return (
    <nav
      aria-label="Jump to section"
      className="sticky top-0 z-30 -mx-6 px-6 py-2 mb-6 bg-neutral-950/90 backdrop-blur border-b border-neutral-900 lg:hidden"
    >
      <ul className="flex gap-2 overflow-x-auto no-scrollbar">
        {sections.map(s => (
          <li key={s.id} className="shrink-0">
            <a
              href={`#${s.id}`}
              aria-current={activeId === s.id ? 'true' : undefined}
              className={[
                'inline-block whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
                activeId === s.id
                  ? 'bg-purple-600 text-white'
                  : 'bg-neutral-900 text-neutral-400 hover:text-neutral-200',
              ].join(' ')}
            >
              {s.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
