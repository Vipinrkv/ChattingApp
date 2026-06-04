-- RLS policies for merchant profile visibility and owner management
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
