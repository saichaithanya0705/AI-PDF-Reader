-- Cross-document recommendations need to exclude the open document *before*
-- the LIMIT is applied; otherwise the open page's own chunks fill every slot.
-- Also skip chunks whose parent document has been soft-deleted.

drop function if exists public.match_document_chunks(
  extensions.vector, uuid, integer, real, uuid
);

create or replace function public.match_document_chunks(
  query_embedding extensions.vector(2048),
  filter_user_id uuid,
  match_count integer default 10,
  match_threshold real default 0.0,
  filter_document_id uuid default null,
  exclude_document_id uuid default null
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
  join public.documents as documents
    on documents.id = chunks.document_id
   and documents.user_id = chunks.user_id
  where chunks.user_id = filter_user_id
    and documents.status <> 'deleted'
    and (filter_document_id is null or chunks.document_id = filter_document_id)
    and (exclude_document_id is null or chunks.document_id <> exclude_document_id)
    and 1 - (chunks.embedding::extensions.halfvec(2048)
      OPERATOR(extensions.<=>) query_embedding::extensions.halfvec(2048)) >= greatest(0.0, least(1.0, match_threshold))
  order by chunks.embedding::extensions.halfvec(2048)
    OPERATOR(extensions.<=>) query_embedding::extensions.halfvec(2048)
  limit greatest(1, least(50, match_count));
$$;

revoke all on function public.match_document_chunks(
  extensions.vector, uuid, integer, real, uuid, uuid
) from public, anon;
grant execute on function public.match_document_chunks(
  extensions.vector, uuid, integer, real, uuid, uuid
) to authenticated, service_role;
