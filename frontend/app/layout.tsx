import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'LYRIQ — AI Music Analyzer',
  description: 'Claude-powered song interpretation',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-neutral-950 min-h-screen`}>
        {children}
      </body>
    </html>
  );
}
