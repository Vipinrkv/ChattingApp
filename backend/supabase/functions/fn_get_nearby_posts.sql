-- Proximity query for nearby public feed posts within a radius
create or replace function fn_get_nearby_posts(
  user_lat double precision,
  user_lng double precision,
  max_distance_meters int default 2000
)
returns table (
  id uuid,
  author_id uuid,
  category text,
  title text,
  body text,
  distance_meters double precision,
  created_at timestamptz
)
language sql stable as $$
  select
    p.id,
    p.author_id,
    p.category,
    p.title,
    p.body,
    st_distance(p.location, st_setsrid(st_makepoint(user_lng, user_lat), 4326)::geography) as distance_meters,
    p.created_at
  from public_feed_posts p
  where p.is_active
    and st_dwithin(p.location, st_setsrid(st_makepoint(user_lng, user_lat), 4326)::geography, max_distance_meters)
  order by distance_meters asc, p.created_at desc;
$$;
