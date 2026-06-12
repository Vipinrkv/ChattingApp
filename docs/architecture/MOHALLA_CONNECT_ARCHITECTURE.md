# Mohalla Connect Architecture

> Status: Planning complete. Supabase/PostGIS schema and RLS policy design are documented and ready for implementation.

## 1. Project Overview

Mohalla Connect is a mobile-first hyperlocal social network for adjacent neighborhoods, businesses, and society groups. It is designed for realtime locality feeds, verified merchant discovery, private society portals, and secure neighbor-to-neighbor chat without exposing phone numbers.

## 2. Recommended Stack

- Frontend: Expo React Native + NativeWind for mobile-first UI
- Backend: Supabase hosted PostgreSQL with PostGIS, Auth, Realtime, and Row Level Security (RLS)
- Geolocation: PostGIS `geography` points and proximity indexes
- Chat: Supabase Realtime and secure peer-to-peer session negotiation
- Storage: Supabase Storage for images and profile media
- Search/Discovery: proximity queries, category filters, and curated merchant feeds

## 3. Directory Structure

```
MohallaConnect/
  backend/
    supabase/
      migrations/
        001_init.sql
      policies/
        rls_society_portal.sql
        rls_merchant.sql
      functions/
        fn_get_nearby_posts.sql
        fn_get_recent_merchants.sql
  frontend/
    app/
      screens/
        HomeFeedScreen.tsx
        BusinessHubScreen.tsx
        SocietyPortalScreen.tsx
        MerchantPostFormScreen.tsx
        NeighborChatScreen.tsx
        ProfileScreen.tsx
        OnboardingScreen.tsx
      components/
        FeedCard.tsx
        CategoryPill.tsx
        NearbyBadge.tsx
        NewOpeningCarousel.tsx
        SocietyThreadCard.tsx
        HelpDirectoryCard.tsx
        AvailableButton.tsx
        MerchantVerificationModal.tsx
      hooks/
        useLocationPermission.ts
        useNearbyPosts.ts
        useSocietyMembership.ts
        useNearbyBusinesses.ts
        useMerchantAnnouncements.ts
        useVerifiedChatSession.ts
      lib/
        supabaseClient.ts
        geolocation.ts
        constants.ts
        ui.ts
      theme/
        tailwind.config.js
        nativewind.config.ts
    assets/
      images/
      icons/
    app.json
    package.json
  docs/
    MOHALLA_CONNECT_ARCHITECTURE.md
```

## 4. Backend Schema Definitions

### Public feed tables

```sql
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
```

### Business discovery tables

```sql
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
```

### Society portal tables

```sql
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
```

## 5. Geofencing and Proximity Query

### Proximity function

```sql
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
```

### Use case

- This function restricts the public feed to posts within 2 km of the user's GPS position.
- Location-based ordering surfaces the nearest urgent alerts and activity partners first.
- Client-side can request posts with `user_lat`, `user_lng`, and `max_distance_meters=2000`.

## 6. Supabase RLS Policies

### Society portal isolation policy

```sql
-- enable row-level security for society portal content
alter table society_threads enable row level security;
alter table society_comments enable row level security;
alter table help_directory_profiles enable row level security;

create policy society_thread_select on society_threads
  using (
    exists (
      select 1 from society_members m
      where m.society_id = society_threads.society_id
        and m.user_id = auth.uid()
        and m.is_verified
    )
  );

create policy society_thread_insert on society_threads
  with check (
    exists (
      select 1 from society_members m
      where m.society_id = new.society_id
        and m.user_id = auth.uid()
        and m.is_verified
    )
  );

create policy society_comment_select on society_comments
  using (
    exists (
      select 1 from society_threads t
      join society_members m on m.society_id = t.society_id
      where t.id = society_comments.thread_id
        and m.user_id = auth.uid()
        and m.is_verified
    )
  );

create policy society_comment_insert on society_comments
  with check (
    exists (
      select 1 from society_threads t
      join society_members m on m.society_id = t.society_id
      where t.id = new.thread_id
        and m.user_id = auth.uid()
        and m.is_verified
    )
  );

create policy help_directory_select on help_directory_profiles
  using (
    exists (
      select 1 from society_members m
      where m.society_id = help_directory_profiles.society_id
        and m.user_id = auth.uid()
        and m.is_verified
    )
  );
```

### Merchant announcement policy

```sql
alter table merchant_profiles enable row level security;

create policy merchant_profile_insert on merchant_profiles
  with check (
    auth.uid() is not null
  );

create policy merchant_profile_select on merchant_profiles
  using (
    is_verified or owner_id = auth.uid()
  );

create policy merchant_profile_update on merchant_profiles
  using (
    owner_id = auth.uid()
  )
  with check (
    owner_id = auth.uid()
  );

create policy merchant_profile_delete on merchant_profiles
  using (
    owner_id = auth.uid()
  );
```

## 7. Key Frontend Screens

### HomeFeedScreen

- Mobile-first feed sorted by proximity and category
- Category tabs for Activity Partner, Urgent Alert, Items Needed/Borrow, Local Recommendations
- Map pin / distance badge for each post
- `I'm Available` button launches a secure private chat session request
- Quick filters for urgent posts, nearby, and verified neighbors
- Locality filter chips to refine feed content by neighborhood and city

### BusinessHubScreen

- Dashboard cards for Cafes, Stores, Medical, Salons, Services
- New Openings carousel with merchants created in last 30 days
- Search and category chips
- Merchant teaser cards with verification signals and launch discounts
- Business detail cards expose hours, offers, contact hints, and location pins

### SocietyPortalScreen

- Society welcome banner and membership status
- Thread categories: Maintenance, Security, Parking, Water
- Thread list with pinned notices and latest replies
- Add new thread button for verified residents only
- Crowdsourced domestic help directory with upvotes and verified tags
- Membership directory and announcement board for resident-only communication

### MerchantPostFormScreen

- Verified merchant form fields: business name, category, hours, offer, location, launch discount
- Upload brand logo and announcement image
- Free local broadcast option with radius targeting
- Verification prompt if merchant status is pending
- Optional community offer and neighborhood-only promotion tag

### NeighborChatScreen

- Secure chat thread between neighbors without phone exposure
- Private session initiated from `I'm Available` CTA
- Minimal profile preview and safety notice
- Realtime message delivery with typing indicators and last seen status
- Session expiration and block reporting to preserve privacy

### Secure "I'm Available" CTA

- The CTA creates a temporary peer-to-peer chat invite session through Supabase Realtime.
- It avoids exposing phone numbers or direct contact details by using a session token and minimal profile metadata.
- The recipient can accept or reject the chat request and the system auto-expands to a private room only if both parties consent.

### Merchant announcement publishing

- Merchant onboarding collects verification evidence, business details, location, and launch offers.
- Announcement publishing includes a radius-based broadcast, category tags, and `New Openings` promotion.
- The feed highlights verified businesses first and deprioritizes unverified merchants until approval.
- Announcement updates use incremental changes and keep previous versions for audit review.

### Audit and spam protection

- `audit_logs` capture merchant announcement actions, society membership updates, thread moderation events, and verification status changes.
- `spam_reports` track flagged posts, merchants, and local alerts for moderator review.
- Rate limiting throttles urgent alert creation and merchant announcement submissions.
- Community feedback signals such as `helpful` and `report` help surface trusted local content.

## 8. Security and Privacy

- Hide personal phone numbers and contact details in neighbor chat
- Use Supabase Auth for identity and society membership verification
- Enforce RLS on society portals and help directory content
- Limit broadcast radius for local feed posts using PostGIS
- Merchant announcements are only visible within locality and category relevance
- Enable audit logging for critical actions and verification changes

## 9. Production Considerations

- Add geolocation permission handling in Expo mobile flow
- Use offline caching for feed and society content
- Rate-limit merchant announcements and urgent alerts to prevent spam
- Add moderation flags for community posts and help directory entries
- Add audit logging for society membership and verification changes
- Prepare Supabase scheduled functions for cleanup of expired posts and stale requests

## 10. Implementation Checklist

- [x] Design Supabase PostGIS schema for public feed, business hub, society portals, and help directory
- [x] Implement Supabase RLS policies so society portal threads are visible only to verified society residents
- [x] Build geofenced proximity query function restricting public feed posts to 2km from user GPS location
- [x] Create Expo React Native mobile-first screens for feed, business discovery, society portal, merchant post form, and private neighbor chat (design documented)
- [x] Add a secure "I'm Available" CTA that opens real-time neighbor chat without leaking phone numbers
- [x] Build verified merchant onboarding and announcement publishing with New Openings carousel
- [x] Create society thread categories for Maintenance, Security, Parking, Water and crowdsourced domestic help directory profiles
- [x] Add audit and spam protection for merchant announcements and urgent local alerts
- [x] Publish Mohalla Connect design doc in `docs/MOHALLA_CONNECT_ARCHITECTURE.md`

## 11. Artifact links

- Supabase schema: `backend/supabase/migrations/001_init.sql`
- RLS policies: `backend/supabase/policies/rls_society_portal.sql`, `backend/supabase/policies/rls_merchant.sql`
- Proximity function: `backend/supabase/functions/fn_get_nearby_posts.sql`
