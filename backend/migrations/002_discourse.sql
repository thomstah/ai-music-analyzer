create table discourse (
  id uuid primary key default gen_random_uuid(),
  song_id uuid not null references songs(id) on delete cascade,
  excerpts jsonb not null,
  scraped_at timestamptz default now()
);
