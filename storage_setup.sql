-- Enable RLS on storage.objects if not already enabled (it is by default usually)
alter table storage.objects enable row level security;

-- Create the bucket 'upload files' if it doesn't exist
insert into storage.buckets (id, name, public)
values ('upload files', 'upload files', true)
on conflict (id) do nothing;

-- POLICY 1: Allow authenticated users to upload files to 'upload files' bucket
create policy "Allow authenticated uploads"
on storage.objects for insert
to authenticated
with check ( bucket_id = 'upload files' );

-- POLICY 2: Allow users to view/download files (public or authenticated)
create policy "Allow public view"
on storage.objects for select
using ( bucket_id = 'upload files' );

-- POLICY 3: Allow users to update their own files
create policy "Allow users to update own files"
on storage.objects for update
to authenticated
using ( bucket_id = 'upload files' and owner = auth.uid() )
with check ( bucket_id = 'upload files' and owner = auth.uid() );

-- POLICY 4: Allow users to delete their own files
create policy "Allow users to delete own files"
on storage.objects for delete
to authenticated
using ( bucket_id = 'upload files' and owner = auth.uid() );
