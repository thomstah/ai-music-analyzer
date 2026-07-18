export default function SongPageSkeleton() {
  return (
    <main
      className="max-w-6xl mx-auto px-6 py-8 relative animate-pulse"
      aria-busy="true"
      aria-label="Loading song"
    >
      {/* Banner — album art + title + metadata rows */}
      <div className="relative overflow-hidden rounded-xl mb-8 min-h-48 bg-neutral-900">
        <div className="relative z-10 flex gap-6 p-6 items-end">
          <div className="hidden sm:block w-[140px] h-[140px] rounded-lg bg-neutral-800 shrink-0" />
          <div className="flex-1 min-w-0 space-y-3">
            <div className="h-3 w-16 rounded bg-neutral-800" />
            <div className="h-8 w-3/4 rounded bg-neutral-800" />
            <div className="h-4 w-1/2 rounded bg-neutral-800" />
            <div className="flex gap-4 pt-2">
              <div className="h-3 w-16 rounded bg-neutral-800" />
              <div className="h-3 w-24 rounded bg-neutral-800" />
              <div className="h-3 w-20 rounded bg-neutral-800" />
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-8 items-start">
        {/* Analysis column */}
        <div className="flex-1 min-w-0 w-full space-y-6">
          <div className="h-14 w-full rounded-xl border border-dashed border-neutral-800" />

          <div className="space-y-3">
            <div className="h-3 w-16 rounded bg-neutral-800" />
            <div className="h-5 w-11/12 rounded bg-neutral-800" />
            <div className="h-5 w-4/5 rounded bg-neutral-800" />
          </div>

          <div className="space-y-3">
            <div className="h-3 w-20 rounded bg-neutral-800" />
            <div className="h-24 w-full rounded-xl bg-neutral-900 border border-neutral-800" />
          </div>

          <div className="space-y-3">
            <div className="h-3 w-24 rounded bg-neutral-800" />
            <div className="h-16 w-full rounded-xl bg-neutral-900 border border-neutral-800" />
            <div className="h-16 w-full rounded-xl bg-neutral-900 border border-neutral-800" />
          </div>
        </div>

        {/* Lyrics column */}
        <aside className="w-full lg:w-96 shrink-0 bg-neutral-900 rounded-xl p-5 space-y-2">
          <div className="h-3 w-14 rounded bg-neutral-800 mb-4" />
          {Array.from({ length: 10 }).map((_, i) => (
            <div
              key={i}
              className="h-3 rounded bg-neutral-800"
              style={{ width: `${65 + ((i * 7) % 30)}%` }}
            />
          ))}
        </aside>
      </div>
    </main>
  );
}
