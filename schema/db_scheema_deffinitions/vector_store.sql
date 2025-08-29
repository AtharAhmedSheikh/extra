
-- Enable the pgvector extension to work with embedding vectors
create extension if not exists vector;

-- Create a table to store all vectors (documents chunks and FAQs)
create table vector_store (
  id bigserial primary key,
  content text not null, -- the actual text content
  embedding vector(1536) not null, -- OpenAI embedding
  content_type varchar(50) not null, -- 'document_chunk' or 'faq'
  reference_id bigint, -- references to company_knowledgebase.id
  metadata jsonb default '{}', -- additional metadata
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

-- Create indexes for efficient searching
create index vector_store_embedding_idx on vector_store using ivfflat (embedding vector_cosine_ops);
create index vector_store_content_type_idx on vector_store (content_type);
create index vector_store_reference_id_idx on vector_store (reference_id);

-- Create a function to search vectors
create or replace function match_vectors (
  query_embedding vector(1536),
  match_count int default 5,
  match_threshold float default 0.3,
  content_type_filter varchar(50) default null
) returns table (
  id bigint,
  content text,
  content_type varchar(50),
  reference_id bigint,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    vector_store.id,
    vector_store.content,
    vector_store.content_type,
    vector_store.reference_id,
    vector_store.metadata,
    1 - (vector_store.embedding <=> query_embedding) as similarity
  from vector_store
  where 
    1 - (vector_store.embedding <=> query_embedding) > match_threshold
    and (content_type_filter is null or vector_store.content_type = content_type_filter)
  order by vector_store.embedding <=> query_embedding
  limit match_count;
end;
$$;
