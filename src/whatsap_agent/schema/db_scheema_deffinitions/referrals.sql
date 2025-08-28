-- Create referrals table
create table if not exists referrals (
    id uuid primary key default gen_random_uuid(),
    total_points integer not null default 0,
    referrer_id text,
    referrer_name text,
    referrer_email text,
    referrer_phone text,
    referral_code text unique,
    referred_users jsonb not null default '[]'::jsonb,
    campaign_id text,
    created_at timestamp with time zone default now()
);

-- Optional: index for faster lookup by referral_code
create index if not exists idx_referrals_referral_code
on referrals(referral_code);

-- Optional: index for JSONB queries (search inside referred_users)
create index if not exists idx_referrals_referred_users
on referrals using gin (referred_users);
