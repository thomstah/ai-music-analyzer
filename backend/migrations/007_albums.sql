create table if not exists albums (
  id uuid primary key default gen_random_uuid(),
  genius_id integer unique,
  title text not null,
  artist text not null,
  release_year text,
  cover_art_url text,
  producers jsonb default '[]'::jsonb,
  tracklist jsonb,
  created_at timestamptz not null default now()
);

create index if not exists albums_genius_id_idx on albums(genius_id);
