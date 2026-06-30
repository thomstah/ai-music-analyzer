interface Props {
  lyrics: string;
}

export default function LyricsPanel({ lyrics }: Props) {
  const lines = lyrics.split('\n');
  return (
    <div className="font-mono text-sm leading-7 text-neutral-300">
      {lines.map((line, i) => (
        <p key={i} className={line.trim() === '' ? 'h-4' : ''}>
          {line || ' '}
        </p>
      ))}
    </div>
  );
}
