create table secrets (
    id uuid primary key default gen_random_uuid(),
    credname text unique not null,
    value text not null,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

-- Enable row level security
alter table secrets enable row level security;

-- Create indexes for better performance
create index secrets_credname_idx on secrets (credname);