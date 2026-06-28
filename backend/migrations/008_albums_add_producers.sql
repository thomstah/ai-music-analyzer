alter table albums add column if not exists producers jsonb default '[]'::jsonb;
