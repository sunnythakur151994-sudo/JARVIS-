create extension if not exists pgcrypto;

create type media_status as enum (
  'discovered','queued','downloading','downloaded','transforming','ready',
  'scheduled','publishing','published','failed','rejected','duplicate','skipped'
);

create table channels (
  id            uuid primary key default gen_random_uuid(),
  display_name  text not null,
  yt_channel_id text unique,
  niche         text,
  oauth_refresh text,                      -- encrypted
  oauth_state   text default 'pending',    -- pending|live|revoked
  timezone      text not null default 'UTC',
  active        boolean default true,
  created_at    timestamptz default now()
);

create table genres (
  id          uuid primary key default gen_random_uuid(),
  channel_id  uuid not null references channels on delete cascade,
  slug        text not null,
  label       text not null,
  weight      int  not null default 1,
  seed_queries text[] not null default '{}',
  hashtags    text[] not null default '{}',
  unique (channel_id, slug)
);

create table source_profiles (
  id             uuid primary key default gen_random_uuid(),
  genre_id       uuid not null references genres on delete cascade,
  platform       text not null check (platform in ('instagram','tiktok','youtube')),
  handle         text not null,
  profile_url    text not null,
  followers      bigint,
  avg_views      bigint,
  score          numeric(6,2),
  cookie_path    text,
  status         text not null default 'candidate'
                 check (status in ('candidate','approved','paused','blocked')),
  last_pull_at   timestamptz,
  pull_cursor    text,
  unique (genre_id, platform, handle)
);

create table media (
  id                uuid primary key default gen_random_uuid(),
  source_profile_id uuid not null references source_profiles on delete cascade,
  genre_id          uuid not null references genres on delete cascade,
  channel_id        uuid not null references channels on delete cascade,
  source_url        text not null,
  platform          text not null,
  source_video_id   text not null,
  sha256            text,
  local_path        text,
  duration_s        numeric(7,2),
  caption           text,
  status            media_status not null default 'discovered',
  reason            text,
  scheduled_at      timestamptz,
  yt_video_id       text,
  yt_privacy        text,
  attempts          int default 0,
  locked_by         text,
  locked_at         timestamptz,
  created_at        timestamptz default now(),
  updated_at        timestamptz default now(),
  unique (channel_id, platform, source_video_id)
);

create unique index media_sha_global on media (sha256) where sha256 is not null;
create index media_queue on media (status, genre_id, created_at);
create index media_slot  on media (scheduled_at) where status in ('scheduled','publishing');
create index media_hash  on media (sha256);

create table upload_log (
  id         bigserial primary key,
  media_id   uuid not null references media on delete cascade,
  from_state media_status,
  to_state   media_status not null,
  note       text,
  actor      text,
  at         timestamptz default now()
);
create index upload_log_media on upload_log (media_id, at desc);

create table slots (
  id          uuid primary key default gen_random_uuid(),
  channel_id  uuid not null references channels on delete cascade,
  genre_id    uuid not null references genres on delete cascade,
  local_time  time not null,
  weekday_mask int not null default 127
);

create table settings (
  channel_id      uuid primary key references channels on delete cascade,
  global_dedupe   boolean default true,
  max_duration_s  int default 58,
  posts_per_day   int default 3,
  watermark_crop  int default 0,
  hook_style      text default 'top-caption',
  publish_lead_h  int default 26
);

alter table media enable row level security;
