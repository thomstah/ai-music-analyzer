import Link from 'next/link';

export default function Footer() {
  return (
    <footer className="mt-16 border-t border-neutral-900">
      <div className="max-w-6xl mx-auto px-6 py-6 text-xs text-neutral-500 space-y-1.5">
        <p>
          Lyriq&apos;s interpretations are AI-generated commentary, not endorsed by
          artists or rights holders.
        </p>
        <p>
          Lyrics and community annotations provided by{' '}
          <a
            href="https://genius.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-neutral-400 hover:text-purple-400 underline underline-offset-2"
          >
            Genius
          </a>
          . Artist and album data via{' '}
          <a
            href="https://www.deezer.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-neutral-400 hover:text-purple-400 underline underline-offset-2"
          >
            Deezer
          </a>
          .
        </p>
        <p className="flex gap-4">
          <Link
            href="/terms"
            className="text-neutral-400 hover:text-purple-400 underline underline-offset-2"
          >
            Terms of Service
          </Link>
          <Link
            href="/privacy"
            className="text-neutral-400 hover:text-purple-400 underline underline-offset-2"
          >
            Privacy Policy
          </Link>
        </p>
      </div>
    </footer>
  );
}
