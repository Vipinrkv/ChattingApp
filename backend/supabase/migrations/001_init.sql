-- Mohalla Connect initial Supabase/PostGIS schema
create extension if not exists postgis;
create extension if not exists pgcrypto;

create table public_feed_posts (
  id uuid primary key default gen_random_uuid(),
  author_id uuid references auth.users(id) not null,
  category text not null check (category in ('Activity Partner','Urgent Alert','Items Needed/Borrow','Local Recommendations')),
  title text not null,
  body text not null,
  location geography(Point, 4326) not null,
  city text not null,
  neighborhood text,
  created_at timestamptz default now() not null,
  expires_at timestamptz,
  is_active boolean default true not null,
  allow_contact boolean default true not null
);
create index idx_public_feed_posts_location on public_feed_posts using gist (location);
create index idx_public_feed_posts_created_at on public_feed_posts (created_at desc);

create table merchant_profiles (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references auth.users(id) not null,
  business_name text not null,
  category text not null check (category in ('Cafes','Stores','Medical','Salons','Services','Other')),
  description text,
  address text,
  location geography(Point, 4326) not null,
  is_verified boolean default false not null,
  opened_at date not null,
  contact_email text,
  discount_offer text,
  created_at timestamptz default now() not null
);
create index idx_merchant_profiles_location on merchant_profiles using gist (location);
create index idx_merchant_profiles_opened_at on merchant_profiles (opened_at desc);

create table societies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  address text not null,
  location geography(Point, 4326) not null,
  verified_resident_tag text,
  created_at timestamptz default now() not null
);
create index idx_societies_location on societies using gist (location);

create table society_members (
  id uuid primary key default gen_random_uuid(),
  society_id uuid references societies(id) not null,
  user_id uuid references auth.users(id) not null,
  is_verified boolean default false not null,
  role text default 'resident' not null,
  joined_at timestamptz default now() not null,
  unique (society_id, user_id)
);

create table society_threads (
  id uuid primary key default gen_random_uuid(),
  society_id uuid references societies(id) not null,
  category text not null check (category in ('Maintenance','Security','Parking','Water')),
  title text not null,
  body text not null,
  created_by uuid references auth.users(id) not null,
  created_at timestamptz default now() not null,
  updated_at timestamptz
);

create table society_comments (
  id uuid primary key default gen_random_uuid(),
  thread_id uuid references society_threads(id) not null,
  author_id uuid references auth.users(id) not null,
  comment text not null,
  created_at timestamptz default now() not null
);

create table help_directory_profiles (
  id uuid primary key default gen_random_uuid(),
  society_id uuid references societies(id) not null,
  service_type text not null check (service_type in ('Electrician','Plumber','Maid','Cook','Housekeeper','Security')),
  name text not null,
  description text,
  contact_hint text,
  rating numeric(3,2) default 0.0 not null,
  upvotes int default 0 not null,
  verified boolean default false not null,
  created_at timestamptz default now() not null
);

create table audit_logs (
  id uuid primary key default gen_random_uuid(),
  entity text not null,
  entity_id uuid,
  action text not null,
  performed_by uuid references auth.users(id),
  details jsonb,
  created_at timestamptz default now() not null
);

create table spam_reports (
  id uuid primary key default gen_random_uuid(),
  entity text not null,
  entity_id uuid not null,
  reported_by uuid references auth.users(id) not null,
  reason text not null,
  status text default 'pending' not null,
  created_at timestamptz default now() not null
);
