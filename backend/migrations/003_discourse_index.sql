create index discourse_song_id_idx on discourse(song_id);
alter table discourse alter column scraped_at set not null;
