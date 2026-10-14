create extension if not exists vector with schema extensions;

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

create or replace function private.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  storage_bucket text not null default 'documents'
    check (storage_bucket = 'documents'),
  storage_key text not null check (length(trim(storage_key)) > 0),
  filename text not null check (length(trim(filename)) > 0),
  original_name text not null check (length(trim(original_name)) > 0),
  mime_type text not null default 'application/pdf'
    check (mime_type = 'application/pdf'),
  file_size bigint not null check (file_size > 0 and file_size <= 104857600),
  file_hash text check (file_hash is null or file_hash ~ '^[0-9a-f]{64}$'),
  status text not null default 'uploaded'
    check (status in ('uploaded', 'processed', 'deleted')),
  processing_status text not null default 'pending'
    check (processing_status in ('pending', 'processing', 'completed', 'failed')),
  persona text,
  job_role text,
  validation_result jsonb,
  metadata jsonb not null default '{}'::jsonb,
  tags text[] not null default '{}'::text[],
  upload_date timestamptz not null default timezone('utc', now()),
  last_uploaded timestamptz,
  last_opened timestamptz,
  last_accessed timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (id, user_id),
  unique (storage_bucket, storage_key)
);

create unique index if not exists documents_user_file_hash_unique
  on public.documents (user_id, file_hash)
  where file_hash is not null and status <> 'deleted';
create index if not exists documents_user_upload_date_idx
  on public.documents (user_id, upload_date desc);
create index if not exists documents_user_status_idx
  on public.documents (user_id, status, processing_status);

drop trigger if exists documents_set_updated_at on public.documents;
create trigger documents_set_updated_at
before update on public.documents
for each row execute function private.set_updated_at();

create table if not exists public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  chunk_text text not null check (length(trim(chunk_text)) > 0),
  chunk_index integer not null check (chunk_index >= 0),
  page_number integer not null check (page_number >= 1),
  embedding extensions.vector(2048) not null,
  char_count integer check (char_count is null or char_count >= 0),
  word_count integer check (word_count is null or word_count >= 0),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  constraint document_chunks_document_owner_fk
    foreign key (document_id, user_id)
    references public.documents(id, user_id)
    on delete cascade,
  unique (document_id, chunk_index)
);

create index if not exists document_chunks_document_idx
  on public.document_chunks (document_id, chunk_index);
create index if not exists document_chunks_user_idx
  on public.document_chunks (user_id, document_id);
create index if not exists document_chunks_text_search_idx
  on public.document_chunks
  using gin (to_tsvector('english', chunk_text));
create index if not exists document_chunks_embedding_hnsw_idx
  on public.document_chunks
  using hnsw ((embedding::extensions.halfvec(2048)) extensions.halfvec_cosine_ops);

alter table public.documents enable row level security;
alter table public.document_chunks enable row level security;

drop policy if exists "documents_select_own" on public.documents;
create policy "documents_select_own"
on public.documents for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "documents_insert_own" on public.documents;
create policy "documents_insert_own"
on public.documents for insert
to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists "documents_update_own" on public.documents;
create policy "documents_update_own"
on public.documents for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "documents_delete_own" on public.documents;
create policy "documents_delete_own"
on public.documents for delete
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "document_chunks_select_own" on public.document_chunks;
create policy "document_chunks_select_own"
on public.document_chunks for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "document_chunks_insert_own" on public.document_chunks;
create policy "document_chunks_insert_own"
on public.document_chunks for insert
to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists "document_chunks_update_own" on public.document_chunks;
create policy "document_chunks_update_own"
on public.document_chunks for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "document_chunks_delete_own" on public.document_chunks;
create policy "document_chunks_delete_own"
on public.document_chunks for delete
to authenticated
using ((select auth.uid()) = user_id);

grant usage on schema public to authenticated, service_role;
grant select, insert, update, delete on public.documents to authenticated;
grant select, insert, update, delete on public.document_chunks to authenticated;
grant all on public.documents, public.document_chunks to service_role;

create or replace function public.match_document_chunks(
  query_embedding extensions.vector(2048),
  filter_user_id uuid,
  match_count integer default 10,
  match_threshold real default 0.0,
  filter_document_id uuid default null
)
returns table (
  id uuid,
  document_id uuid,
  chunk_text text,
  chunk_index integer,
  page_number integer,
  similarity real,
  metadata jsonb
)
language sql
stable
security invoker
set search_path = ''
as $$
  select
    chunks.id,
    chunks.document_id,
    chunks.chunk_text,
    chunks.chunk_index,
    chunks.page_number,
    (1 - (chunks.embedding::extensions.halfvec(2048)
      OPERATOR(extensions.<=>) query_embedding::extensions.halfvec(2048)))::real as similarity,
    chunks.metadata
  from public.document_chunks as chunks
  where chunks.user_id = filter_user_id
    and (filter_document_id is null or chunks.document_id = filter_document_id)
    and 1 - (chunks.embedding::extensions.halfvec(2048)
      OPERATOR(extensions.<=>) query_embedding::extensions.halfvec(2048)) >= greatest(0.0, least(1.0, match_threshold))
  order by chunks.embedding::extensions.halfvec(2048)
    OPERATOR(extensions.<=>) query_embedding::extensions.halfvec(2048)
  limit greatest(1, least(50, match_count));
$$;

revoke all on function public.match_document_chunks(
  extensions.vector, uuid, integer, real, uuid
) from public, anon;
grant execute on function public.match_document_chunks(
  extensions.vector, uuid, integer, real, uuid
) to authenticated, service_role;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('documents', 'documents', false, 104857600, array['application/pdf'])
on conflict (id) do update
set public = false,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "documents_storage_select_own" on storage.objects;
create policy "documents_storage_select_own"
on storage.objects for select
to authenticated
using (
  bucket_id = 'documents'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);

drop policy if exists "documents_storage_insert_own" on storage.objects;
create policy "documents_storage_insert_own"
on storage.objects for insert
to authenticated
with check (
  bucket_id = 'documents'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);

drop policy if exists "documents_storage_delete_own" on storage.objects;
create policy "documents_storage_delete_own"
on storage.objects for delete
to authenticated
using (
  bucket_id = 'documents'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);
