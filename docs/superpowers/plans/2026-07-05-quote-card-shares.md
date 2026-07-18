# Shareable Quote Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users share a specific key-lyric breakdown as a social image. Each breakdown gets its own deep-link URL; opening it in a social preview (or copying the link) shows a Lyriq-branded card built from the album's accent color, the quoted lyric, and the breakdown text.

**Architecture:** Add a Next.js dynamic route `/song/[id]/breakdown/[idx]` with an `opengraph-image.tsx` sibling — Next generates the PNG at request time via `@vercel/og`. No backend changes. Each existing `BreakdownCard` gets a small "Share" affordance that copies the deep-link to the clipboard.

**Tech Stack:** Next.js App Router metadata routes, `@vercel/og` (already Next-bundled on Vercel, or add as a dep if self-hosting), existing `Song` fetch flow.

**Non-goals:** No Twitter-specific card size (OpenGraph is used as the twitter:image fallback and is fine for a portfolio launch). No server-side rendering of breakdown content beyond metadata — the human-facing `page.tsx` reuses existing components.

---

## File Structure

- **Create:** `frontend/app/song/[id]/breakdown/[idx]/page.tsx` — thin page that renders the song page with a `?highlight` scroll hint (or, simplest: redirects to the song page anchored at `#key-lines`).
- **Create:** `frontend/app/song/[id]/breakdown/[idx]/opengraph-image.tsx` — `@vercel/og` handler.
- **Create:** `frontend/lib/quote-card.ts` — pure helper: builds the props the OG renderer needs from a `Song` and an index. Kept separate so it's testable without hitting `ImageResponse`.
- **Modify:** `frontend/components/BreakdownCard.tsx` — add a "Share" button that copies the deep-link.
- **Modify:** `frontend/package.json` — add `@vercel/og` if not already present.

---

### Task 1: Add `@vercel/og` dependency

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

- [ ] **Step 1: Check whether it's already available**

Run: `cd frontend && node -e "console.log(require('@vercel/og'))" 2>&1 | head -5`
Expected: If it errors with `Cannot find module`, proceed to Step 2. If it prints an object, skip to Task 2.

- [ ] **Step 2: Install**

Run: `cd frontend && npm install @vercel/og`
Expected: adds `@vercel/og` under `dependencies`.

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(quote-cards): add @vercel/og for OpenGraph images"
```

---

### Task 2: Pure helper — `buildQuoteCardProps`

**Files:**
- Create: `frontend/lib/quote-card.ts`
- Create: `frontend/lib/__tests__/quote-card.test.ts` (only if a jest/vitest setup exists — see Step 1 check)

- [ ] **Step 1: Check test framework availability**

Run: `cd frontend && node -e "console.log(require('./package.json').scripts.test || 'none')"`
Expected: prints the test script if one is configured; if it prints `none`, skip Step 2 and hand-verify the helper via Task 3.

- [ ] **Step 2: Write the failing test (if a framework is present)**

Create `frontend/lib/__tests__/quote-card.test.ts`:

```typescript
import { buildQuoteCardProps } from '../quote-card';
import type { Song } from '@/types/song';

const song: Song = {
  id: 's1',
  title: 'Runaway',
  artist: 'Kanye West',
  lyrics: '',
  genius_id: null,
  created_at: '',
  interpretation: {
    overall_meaning: '',
    emotional_tone: '',
    themes: [],
    key_lyric_breakdowns: [
      { lyric: 'Let’s have a toast for the douchebags', breakdown: 'A biting self-portrait.' },
      { lyric: 'Run away as fast as you can', breakdown: 'A warning to the woman he loves.' },
    ],
  },
  community_commentary: null,
  metadata: {
    artist_id: null, album_id: null, album_art_url: 'https://cdn/x.jpg',
    album_name: null, release_year: null, producer: null,
    accent_color: '#a34fbc',
  },
};

test('picks the breakdown at the given index and passes through accent', () => {
  const props = buildQuoteCardProps(song, 1);
  expect(props).not.toBeNull();
  expect(props!.lyric).toBe('Run away as fast as you can');
  expect(props!.breakdown).toBe('A warning to the woman he loves.');
  expect(props!.accent).toBe('#a34fbc');
  expect(props!.title).toBe('Runaway');
});

test('returns null when the index is out of range', () => {
  expect(buildQuoteCardProps(song, 5)).toBeNull();
});

test('truncates long breakdown text with an ellipsis', () => {
  const long = 'a'.repeat(500);
  const s = { ...song, interpretation: { ...song.interpretation!,
    key_lyric_breakdowns: [{ lyric: 'x', breakdown: long }] } };
  const props = buildQuoteCardProps(s, 0);
  expect(props!.breakdown.length).toBeLessThanOrEqual(183);
  expect(props!.breakdown.endsWith('…')).toBe(true);
});
```

- [ ] **Step 3: Implement the helper**

Create `frontend/lib/quote-card.ts`:

```typescript
import type { Song } from '@/types/song';

export interface QuoteCardProps {
  title: string;
  artist: string;
  albumArt: string | null;
  accent: string;
  lyric: string;
  breakdown: string;
}

const DEFAULT_ACCENT = '#7c3aed'; // Tailwind purple-600 — matches the Lyriq wordmark
const MAX_BREAKDOWN = 180;

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max).trimEnd() + '…';
}

export function buildQuoteCardProps(song: Song, idx: number): QuoteCardProps | null {
  const breakdowns = song.interpretation?.key_lyric_breakdowns;
  if (!breakdowns || idx < 0 || idx >= breakdowns.length) return null;
  const entry = breakdowns[idx];
  return {
    title: song.title,
    artist: song.artist,
    albumArt: song.metadata?.album_art_url ?? null,
    accent: song.metadata?.accent_color ?? DEFAULT_ACCENT,
    lyric: entry.lyric,
    breakdown: truncate(entry.breakdown, MAX_BREAKDOWN),
  };
}
```

- [ ] **Step 4: Run the test (if applicable)**

Run: `cd frontend && npm test -- quote-card`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/quote-card.ts frontend/lib/__tests__/quote-card.test.ts
git commit -m "feat(quote-cards): pure helper for building card props"
```

---

### Task 3: `/song/[id]/breakdown/[idx]` deep-link page

**Files:**
- Create: `frontend/app/song/[id]/breakdown/[idx]/page.tsx`

The page's real purpose is to give the OG image a URL to attach to. For users who visit directly, redirect them to the song page anchored at the key-lines section.

- [ ] **Step 1: Create the page**

```tsx
import { redirect } from 'next/navigation';

export default function BreakdownDeepLink({
  params,
}: { params: { id: string; idx: string } }) {
  redirect(`/song/${params.id}#key-lines`);
}
```

- [ ] **Step 2: Verify in the browser**

Run: `cd frontend && npm run dev`
Visit: `http://localhost:3000/song/<any-existing-song-id>/breakdown/0`
Expected: redirected to `/song/<id>#key-lines` and the page scrolls to Key Lines.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/song/[id]/breakdown/[idx]/page.tsx
git commit -m "feat(quote-cards): breakdown deep-link redirects to key-lines"
```

---

### Task 4: `opengraph-image.tsx` — render the PNG

**Files:**
- Create: `frontend/app/song/[id]/breakdown/[idx]/opengraph-image.tsx`

- [ ] **Step 1: Create the image handler**

```tsx
import { ImageResponse } from 'next/og';
import { getSongById } from '@/lib/api';
import { buildQuoteCardProps } from '@/lib/quote-card';

export const runtime = 'edge';
export const contentType = 'image/png';
export const size = { width: 1200, height: 630 };
export const alt = 'Lyriq — song analysis card';

export default async function Image({
  params,
}: { params: { id: string; idx: string } }) {
  const song = await getSongById(params.id);
  const idx = parseInt(params.idx, 10);
  const props = song ? buildQuoteCardProps(song, Number.isFinite(idx) ? idx : -1) : null;

  if (!props) {
    // Fallback card so the URL always resolves to a valid image.
    return new ImageResponse(
      (
        <div style={{
          width: '100%', height: '100%', display: 'flex',
          alignItems: 'center', justifyContent: 'center',
          background: '#0a0a0a', color: '#a78bfa',
          fontSize: 72, fontWeight: 800, letterSpacing: '0.2em',
        }}>
          LYRIQ
        </div>
      ),
      size,
    );
  }

  return new ImageResponse(
    (
      <div style={{
        width: '100%', height: '100%', display: 'flex', flexDirection: 'column',
        background: `linear-gradient(135deg, ${props.accent} 0%, #0a0a0a 70%)`,
        color: 'white', padding: 64, fontFamily: 'sans-serif',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          {props.albumArt && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={props.albumArt} width={120} height={120} style={{ borderRadius: 12 }} alt="" />
          )}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ fontSize: 44, fontWeight: 800, lineHeight: 1.1 }}>{props.title}</div>
            <div style={{ fontSize: 28, opacity: 0.85, marginTop: 8 }}>{props.artist}</div>
          </div>
        </div>

        <div style={{
          marginTop: 48, fontStyle: 'italic', fontSize: 40, lineHeight: 1.3,
          borderLeft: '6px solid rgba(255,255,255,0.6)', paddingLeft: 24,
          display: 'flex',
        }}>
          “{props.lyric}”
        </div>

        <div style={{ marginTop: 32, fontSize: 26, lineHeight: 1.4, opacity: 0.88, display: 'flex' }}>
          {props.breakdown}
        </div>

        <div style={{
          marginTop: 'auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div style={{ fontSize: 22, opacity: 0.6, display: 'flex' }}>lyriq — song analysis</div>
          <div style={{
            fontSize: 22, fontWeight: 800, letterSpacing: '0.25em',
            color: 'white', opacity: 0.85, display: 'flex',
          }}>
            LYRIQ
          </div>
        </div>
      </div>
    ),
    size,
  );
}
```

- [ ] **Step 2: Verify the image renders**

Run: `cd frontend && npm run dev`
Open: `http://localhost:3000/song/<any-existing-song-id>/breakdown/0/opengraph-image`
Expected: a 1200×630 PNG downloads/renders showing the accent gradient, title/artist, italic quoted lyric, and breakdown text.

Also verify with a social debugger (once deployed): paste `/song/<id>/breakdown/0` into https://www.opengraph.xyz/ and confirm the image shows.

- [ ] **Step 3: Commit**

```bash
git add "frontend/app/song/[id]/breakdown/[idx]/opengraph-image.tsx"
git commit -m "feat(quote-cards): opengraph-image handler for breakdown deep-links"
```

---

### Task 5: `Share` button on `BreakdownCard`

**Files:**
- Modify: `frontend/components/BreakdownCard.tsx`

- [ ] **Step 1: Add index prop + share handler**

First inspect the current signature:

Run: `cd frontend && sed -n '1,60p' components/BreakdownCard.tsx`

The component currently receives `lyric` and `breakdown`. Extend it to take `songId` and `index`:

```tsx
'use client';
import { useState } from 'react';

export default function BreakdownCard({
  lyric,
  breakdown,
  songId,
  index,
}: {
  lyric: string;
  breakdown: string;
  songId: string;
  index: number;
}) {
  const [copied, setCopied] = useState(false);

  async function handleShare() {
    const url = `${window.location.origin}/song/${songId}/breakdown/${index}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard blocked — fall back to prompt so the user can still grab it.
      window.prompt('Copy this link:', url);
    }
  }

  return (
    <div className="border-l-2 border-purple-500 pl-5 py-2 my-6">
      <p className="font-serif italic text-neutral-100 text-lg leading-relaxed">
        &ldquo;{lyric}&rdquo;
      </p>
      <p className="text-neutral-300 text-sm leading-relaxed mt-3">{breakdown}</p>
      <button
        onClick={handleShare}
        className="mt-3 text-[11px] uppercase tracking-widest text-neutral-500 hover:text-purple-300 transition-colors"
      >
        {copied ? 'Link copied ✓' : 'Share this breakdown'}
      </button>
    </div>
  );
}
```

**Note:** the JSX above is the intended final shape. If `BreakdownCard.tsx` currently uses different Tailwind classes for the quote block, preserve them and only add the button and the `useState` import; do not restyle the quote itself in this task.

- [ ] **Step 2: Update callers to pass `songId` and `index`**

Run: `cd frontend && grep -rn "<BreakdownCard" components/ app/`
For each usage (there should be one in `AnalysisPanel.tsx` mapping over `key_lyric_breakdowns`), pass the map index and the song id. If `AnalysisPanel` doesn't currently receive `songId`, add it as a prop and thread it through from `song/[id]/page.tsx`.

Example edit in `AnalysisPanel.tsx`:

```tsx
{interpretation.key_lyric_breakdowns.map((b, i) => (
  <BreakdownCard
    key={i}
    lyric={b.lyric}
    breakdown={b.breakdown}
    songId={songId}
    index={i}
  />
))}
```

And in the caller (`song/[id]/page.tsx`):

```tsx
<AnalysisPanel
  interpretation={song.interpretation}
  commentary={song.community_commentary}
  onRequestDeepAnalysis={handleRequestDeep}
  deepAnalysisLoading={deepLoading}
  deepAnalysisError={deepError}
  songId={song.id}
/>
```

Add `songId: string;` to the `AnalysisPanel` props interface.

- [ ] **Step 3: Manual verify**

Run: `cd frontend && npm run dev`
Load a song with a Claude interpretation. Click "Share this breakdown" under any breakdown — the button should show "Link copied ✓". Paste the copied URL into a new tab; it should redirect to `/song/<id>#key-lines`. Paste it into a link-preview debugger (once deployed) and confirm the OG image renders.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/BreakdownCard.tsx frontend/components/AnalysisPanel.tsx frontend/app/song/[id]/page.tsx
git commit -m "feat(quote-cards): Share button copies breakdown deep-link"
```

---

### Task 6: Attach OG metadata to song pages

**Files:**
- Modify: `frontend/app/song/[id]/page.tsx`

Making the song page itself a good social preview requires a `generateMetadata` export. Since the page is currently a Client Component (`'use client'`), split the metadata into a parent Server Component or convert.

- [ ] **Step 1: Decide split vs conversion**

Least-invasive: keep `page.tsx` client, add a `layout.tsx` in the same folder that owns `generateMetadata`. That layout can fetch the song server-side and set OG tags. Body remains the client component.

Create `frontend/app/song/[id]/layout.tsx`:

```tsx
import type { Metadata } from 'next';
import { getSongById } from '@/lib/api';

export async function generateMetadata(
  { params }: { params: { id: string } }
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
```

The breakdown deep-link route `/song/[id]/breakdown/[idx]` will inherit this song-level metadata *and* provide its own `opengraph-image` — Next will prefer the more-specific image automatically.

- [ ] **Step 2: Verify metadata**

Run: `cd frontend && npm run build && npm run start`
Visit a song URL, view source, confirm `<meta property="og:title">` and `<meta property="og:image">` are present. The `og:image` for the breakdown route should point at `/song/<id>/breakdown/<idx>/opengraph-image`.

- [ ] **Step 3: Commit**

```bash
git add "frontend/app/song/[id]/layout.tsx"
git commit -m "feat(quote-cards): OpenGraph metadata for song and breakdown routes"
```
