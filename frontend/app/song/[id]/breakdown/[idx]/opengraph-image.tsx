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
    return new ImageResponse(
      (
        <div
          style={{
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#0a0a0a',
            color: '#a78bfa',
            fontSize: 72,
            fontWeight: 800,
            letterSpacing: '0.2em',
          }}
        >
          LYRIQ
        </div>
      ),
      size,
    );
  }

  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          background: `linear-gradient(135deg, ${props.accent} 0%, #0a0a0a 70%)`,
          color: 'white',
          padding: 64,
          fontFamily: 'sans-serif',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          {props.albumArt && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={props.albumArt}
              width={120}
              height={120}
              style={{ borderRadius: 12 }}
              alt=""
            />
          )}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ fontSize: 44, fontWeight: 800, lineHeight: 1.1 }}>{props.title}</div>
            <div style={{ fontSize: 28, opacity: 0.85, marginTop: 8 }}>{props.artist}</div>
          </div>
        </div>

        <div
          style={{
            marginTop: 48,
            fontStyle: 'italic',
            fontSize: 40,
            lineHeight: 1.3,
            borderLeft: '6px solid rgba(255,255,255,0.6)',
            paddingLeft: 24,
            display: 'flex',
          }}
        >
          “{props.lyric}”
        </div>

        <div
          style={{
            marginTop: 32,
            fontSize: 26,
            lineHeight: 1.4,
            opacity: 0.88,
            display: 'flex',
          }}
        >
          {props.breakdown}
        </div>

        <div
          style={{
            marginTop: 'auto',
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
          }}
        >
          <div
            style={{
              fontSize: 22,
              fontWeight: 800,
              letterSpacing: '0.25em',
              color: 'white',
              opacity: 0.85,
              display: 'flex',
            }}
          >
            LYRIQ
          </div>
        </div>
      </div>
    ),
    size,
  );
}
