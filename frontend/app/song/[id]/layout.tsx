import type { Metadata } from 'next';
import { getSongById } from '@/lib/api';

export async function generateMetadata(
  { params }: { params: { id: string } },
): Promise<Metadata> {
  const song = await getSongById(params.id);
  if (!song) return { title: 'Lyriq' };
  const title = `${song.title} — ${song.artist} · Lyriq`;
  const description = song.interpretation?.tldr ?? 'AI-powered lyric analysis on Lyriq.';
  return {
    title,
    description,
    openGraph: { title, description, type: 'article' },
    twitter: { card: 'summary_large_image', title, description },
  };
}

export default function SongLayout({ children }: { children: React.ReactNode }) {
  return children;
}
