'use client';
import { useEffect, useRef, useState } from 'react';

interface Props {
  text: string;
  className?: string;
}

/**
 * Renders text that scrolls horizontally when it would otherwise be clipped.
 * Uses a hidden measurement span so the overflow check is stable regardless
 * of whether the visible content is in marquee mode.
 */
export default function MarqueeText({ text, className = '' }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const measureRef = useRef<HTMLSpanElement>(null);
  const [overflow, setOverflow] = useState(false);

  useEffect(() => {
    const container = containerRef.current;
    const measure = measureRef.current;
    if (!container || !measure) return;

    const check = () => {
      setOverflow(measure.scrollWidth > container.clientWidth + 1);
    };

    check();
    const ro = new ResizeObserver(check);
    ro.observe(container);
    return () => ro.disconnect();
  }, [text]);

  return (
    <div ref={containerRef} className={`relative overflow-hidden whitespace-nowrap ${className}`}>
      {/* Hidden, always-natural-width measurement span */}
      <span
        ref={measureRef}
        aria-hidden
        className="absolute invisible whitespace-nowrap pointer-events-none"
      >
        {text}
      </span>

      {overflow ? (
        <span className="inline-block animate-marquee">
          <span>{text}</span>
          <span className="px-8" aria-hidden>{text}</span>
        </span>
      ) : (
        <span>{text}</span>
      )}
    </div>
  );
}
