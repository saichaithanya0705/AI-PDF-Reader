create or replace function public.search_document_chunks_fts(
  search_query text,
  filter_user_id uuid,
  match_count integer default 20,
  filter_document_id uuid default null,
  exclude_document_id uuid default null
)
returns table (
  chunk_id uuid,
  document_id uuid,
  chunk_text text,
  chunk_index integer,
  page_number integer,
  client_id uuid,
  filename text,
  original_name text,
  file_path text,
  upload_date timestamptz,
  last_uploaded timestamptz,
  last_opened timestamptz,
  last_accessed timestamptz,
  bm25_score real,
  metadata jsonb
)
language sql
stable
security invoker
set search_path = ''
as $$
  select
    chunks.id as chunk_id,
    chunks.document_id,
    chunks.chunk_text,
    chunks.chunk_index,
    chunks.page_number,
    chunks.user_id as client_id,
    documents.filename,
    documents.original_name,
    'supabase://' || documents.storage_bucket || '/' || documents.storage_key as file_path,
    documents.upload_date,
    documents.last_uploaded,
    documents.last_opened,
    documents.last_accessed,
    ts_rank_cd(
      to_tsvector('english', chunks.chunk_text),
      websearch_to_tsquery('english', search_query)
    )::real as bm25_score,
    chunks.metadata
  from public.document_chunks as chunks
  join public.documents as documents
    on documents.id = chunks.document_id
   and documents.user_id = chunks.user_id
  where chunks.user_id = filter_user_id
    and documents.status <> 'deleted'
    and websearch_to_tsquery('english', search_query)
      @@ to_tsvector('english', chunks.chunk_text)
    and (filter_document_id is null or chunks.document_id = filter_document_id)
    and (exclude_document_id is null or chunks.document_id <> exclude_document_id)
  order by ts_rank_cd(
    to_tsvector('english', chunks.chunk_text),
    websearch_to_tsquery('english', search_query)
  ) desc
  limit greatest(1, least(100, match_count));
$$;

revoke all on function public.search_document_chunks_fts(
  text, uuid, integer, uuid, uuid
) from public, anon;
grant execute on function public.search_document_chunks_fts(
  text, uuid, integer, uuid, uuid
) to authenticated, service_role;
