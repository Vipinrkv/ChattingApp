-- RLS policies for society portal content and membership validation
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
