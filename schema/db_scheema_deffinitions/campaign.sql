create table campaigns (
    id text primary key,
    name text not null,
    prizes text[] not null,
    description text,
    start_date timestamp with time zone not null,
    end_date timestamp with time zone not null,
    status boolean not null,
    created_by text not null,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);
