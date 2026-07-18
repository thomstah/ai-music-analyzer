'use client';
import { useEffect, useState } from 'react';
import { getStatus } from '@/lib/api';

export default function GlobalStatusBar() {
  const [degraded, setDegraded] = useState(false);
  const [resetsOn, setResetsOn] = useState<string | null>(null);

  useEffect(() => {
    getStatus().then(s => {
      if (!s) return;
      setDegraded(s.degraded);
      setResetsOn(s.claude_budget.resets_on);
    });
  }, []);

  if (!degraded) return null;

  return (
    <div className="bg-amber-950/60 border-b border-amber-800/60 px-6 py-2 text-center text-amber-200 text-xs">
      Lyriq&apos;s monthly analysis budget is out — browsing still works.
      {resetsOn && ` New analyses resume on ${resetsOn}.`}
    </div>
  );
}
