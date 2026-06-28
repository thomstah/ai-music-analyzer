create table if not exists artists (
  id uuid primary key default gen_random_uuid(),
  genius_id integer unique,
  deezer_id integer,
  name text not null,
  alternate_names jsonb default '[]'::jsonb,
  image_url text,
  header_image_url text,
  description_preview text,
  top_songs jsonb default '[]'::jsonb,
  top_albums jsonb default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists artists_genius_id_idx on artists(genius_id);
