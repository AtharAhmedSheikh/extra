
-- Create a table to store document and FAQ metadata
create table company_knowledgebase (
  id bigserial primary key,
  title varchar(255) not null,
  content_type varchar(50) not null, -- 'document' or 'faq'
  category varchar(100) default 'general',
  
  -- Document-specific fields
  filename varchar(255),
  document_type varchar(50),
  total_chunks int default 0,
  original_content_length int default 0,
  
  -- FAQ-specific fields
  question text,
  answer text,
  keywords text[],
  
  -- Common metadata
  metadata jsonb default '{}',
  is_active boolean default true,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

-- Create indexes
create index company_knowledgebase_content_type_idx on company_knowledgebase (content_type);
create index company_knowledgebase_category_idx on company_knowledgebase (category);
create index company_knowledgebase_is_active_idx on company_knowledgebase (is_active);
create index company_knowledgebase_keywords_idx on company_knowledgebase using gin (keywords);
