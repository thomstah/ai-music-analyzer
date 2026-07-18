'use client';
import { useEffect, useState } from 'react';

const INITIAL = 'Finding the song…';

const STAGES: Array<{ atMs: number; message: string }> = [
  { atMs: 1200, message: 'Fetching lyrics…' },
  { atMs: 2600, message: 'Reading community discussion…' },
  { atMs: 4500, message: 'Extracting themes…' },
  { atMs: 6500, message: 'Almost there…' },
];

export function useAnalyzeProgress(active: boolean): string {
  const [message, setMessage] = useState(INITIAL);

  useEffect(() => {
    if (!active) {
      setMessage(INITIAL);
      return;
    }
    const timers = STAGES.map(({ atMs, message: m }) =>
      setTimeout(() => setMessage(m), atMs),
    );
    return () => timers.forEach(clearTimeout);
  }, [active]);

  return message;
}
