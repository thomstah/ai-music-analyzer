'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body style={{ backgroundColor: '#0a0a0a', color: '#e5e5e5', margin: 0, fontFamily: 'sans-serif' }}>
        <main style={{ maxWidth: 640, margin: '0 auto', padding: '96px 24px', textAlign: 'center' }}>
          <p style={{ fontSize: 12, fontWeight: 700, color: '#c084fc', textTransform: 'uppercase', letterSpacing: '0.2em', marginBottom: 12 }}>
            Something broke
          </p>
          <h1 style={{ fontSize: 30, fontWeight: 900, color: 'white', marginBottom: 16 }}>
            Lyriq couldn&apos;t start.
          </h1>
          <p style={{ fontSize: 14, color: '#a3a3a3', lineHeight: 1.6, marginBottom: 32 }}>
            Something crashed before the page could even render. Reload the page
            — if it keeps happening, try again in a few minutes.
          </p>
          <button
            onClick={reset}
            style={{
              background: '#9333ea',
              color: 'white',
              fontSize: 14,
              fontWeight: 500,
              padding: '10px 20px',
              borderRadius: 9999,
              border: 'none',
              cursor: 'pointer',
            }}
          >
            Try again
          </button>
          {error.digest && (
            <p style={{ marginTop: 40, fontSize: 10, fontFamily: 'monospace', color: '#525252' }}>
              ref {error.digest}
            </p>
          )}
        </main>
      </body>
    </html>
  );
}
